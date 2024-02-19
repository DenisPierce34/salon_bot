import telebot
from telebot import types
import mysql.connector
from datetime import datetime
from my_calendar import create_keyboard_with_calendar, callback_query_data, callback_query_hour

db = mysql.connector.connect(
    host="",
    user="",
    password="",
    database=""
)
cursor = db.cursor()

bot = telebot.TeleBot('')

Date = None
Hour = None
Master = []


# Функция для обработки команды /start
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Добро пожаловать в наш салон красоты!\n Для того, чтобы записаться на приём "
                                      "выберите из списка меню \"Наши услуги\"", reply_markup=None)
    # bot.send_message(message.chat.id, " /", reply_markup=empty_keyboard)


# Функция для обработки команды /services
@bot.message_handler(commands=['services'])
def ask_service(message):
    cursor.execute("SELECT * FROM services")
    services = cursor.fetchall()
    keyboard = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True, one_time_keyboard=True)
    for service in services:
        keyboard.add(telebot.types.KeyboardButton(service[1]))
    bot.send_message(message.chat.id, "Выберите услугу:", reply_markup=keyboard)


# Обработчик команды /clear
@bot.message_handler(commands=['clear'])
def delete_message(message):
    # Удаление сообщения, отправленного ботом
    bot.send_message(message.chat.id, "Удалить переписку вы сможете лишь самостоятельно.\n"
                                      "Если используете ", reply_markup=types.ReplyKeyboardRemove())


@bot.message_handler(func=lambda message: True)
def handle_service(message):
    # Получаем все услуги из базы данных
    cursor.execute("SELECT name FROM services")
    services = [row[0] for row in cursor.fetchall()]
    # Проверяем, входит ли message.text в список значений из базы данных
    if message.text in services:
        cursor.execute("SELECT masters.id, masters.fio, masters.phone, services.id FROM masters "
                       "INNER JOIN services ON masters.service_id = services.id "
                       "WHERE services.name = %s", (message.text,))
        masters = cursor.fetchall()
        keyboard = telebot.types.InlineKeyboardMarkup()

        for master in masters:
            keyboard.add(
                telebot.types.InlineKeyboardButton(text=master[1], callback_data=f"master_id:{str(master[0])}"))
        bot.send_message(message.chat.id, "Выберите мастера:", reply_markup=keyboard)


def handle_master(call):
    master_id = int(call.data.split(":")[1])
    cursor.execute("SELECT * FROM masters WHERE id = %s", (master_id,))
    master = cursor.fetchone()
    bot.edit_message_text("Выберите дату для записи:", call.message.chat.id, call.message.message_id,
                          reply_markup=create_keyboard_with_calendar(datetime.now()))
    return master


def get_available_time_slots(master_id):
    current_date = datetime.now().strftime('%Y-%m-%d')
    cursor.execute("SELECT dt FROM visits WHERE master_id = %s AND DATE(dt) = %s",
                   (master_id, current_date))

    occupied_time_slots = [visit[0].strftime('%H:%M') for visit in cursor.fetchall()]
    all_time_slots = [f"{hour}:00" for hour in range(10, 22)]
    available_time_slots = [time_slot for time_slot in all_time_slots if time_slot not in occupied_time_slots]

    return available_time_slots


def handle_time(message, **kwargs):
    time = message.text
    master_id = kwargs['master_id']
    service_id = kwargs['service_id']

    # Save the selected time, master, and service
    kwargs['time'] = time
    kwargs['master_id'] = master_id
    kwargs['service_id'] = service_id

    bot.register_next_step_handler_by_chat_id(message.chat.id, handle_phone_number, **kwargs)


def handle_phone_number(message, **kwargs):
    phone_number = message.text
    master_id = kwargs['master_id']
    time = kwargs['time']
    service_id = kwargs['service_id']

    # Save the client's phone number
    client_id = save_client(message.chat.id, message.chat.first_name, phone_number, message.chat.last_name)

    # Save the visit
    save_visit(client_id, master_id, time, service_id)

    # Send the success message
    bot.send_message(message.chat.id, f"Вы успешно записаны к мастеру: {Master[1]} на {Date} в {Hour}",
                     reply_markup=types.ReplyKeyboardRemove())


def is_time_slot_available(master_id, time):
    dt = datetime.now().strftime('%Y-%m-%d') + " " + time + ":00"
    cursor.execute("SELECT * FROM visits WHERE master_id = %s AND dt = %s",
                   (master_id, dt))
    return cursor.fetchone() is None


def save_client(chat_id, first_name, phone_number, last_name=''):
    cursor.execute("SELECT * FROM clients WHERE telegram_id = %s", (str(chat_id),))
    existing_client = cursor.fetchone()

    if existing_client:
        return existing_client[0]
    else:
        cursor.execute("INSERT INTO clients (fio, telegram_id, phone) VALUES (%s, %s, %s)",
                       (first_name + ' ' + last_name, str(chat_id), phone_number))
        db.commit()
        return cursor.lastrowid


def save_visit(client_id, master_id, time, service_id):
    cursor.execute("SELECT material_id FROM services WHERE id = %s", (service_id,))
    material_id = cursor.fetchone()[0]

    dt = datetime.now().strftime('%Y-%m-%d') + " " + time + ":00"
    cursor.execute("INSERT INTO visits (client_id, master_id, dt, service_id, material_id) VALUES (%s, %s, %s, %s, %s)",
                   (client_id, master_id, dt, service_id, material_id))

    db.commit()


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data != "IGNORE" and not call.data.startswith("hour:") and not call.data.startswith("master_id:"):
        global Date
        Date = callback_query_data(call)
    elif call.data.startswith("hour:"):
        global Hour
        Hour = callback_query_hour(call)
    elif call.data.startswith("master_id:"):
        global Master
        Master = handle_master(call)
        handle_time(call.message, master_id=Master[0], service_id=Master[3])


try:
    bot.polling(non_stop=True)
except Exception as e:
    print(f"Произошла ошибка при запуске бота: {e}")
