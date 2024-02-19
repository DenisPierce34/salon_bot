import telebot
from datetime import datetime, timedelta
from telebot import types
import calendar
from dateutil.relativedelta import relativedelta
import time

# Создаем экземпляр бота
bot = telebot.TeleBot('')


# Функция для создания клавиатуры с календарем на основе выбранной даты
def create_keyboard_with_calendar(selected_date):
    # Словарь соответствия английских и русских названий месяцев
    translation_dict = {
        1: "Январь",
        2: "Февраль",
        3: "Март",
        4: "Апрель",
        5: "Май",
        6: "Июнь",
        7: "Июль",
        8: "Август",
        9: "Сентябрь",
        10: "Октябрь",
        11: "Ноябрь",
        12: "Декабрь"
    }
    # Устанавливаем количество кнопок в строке клавиатуры = 7
    markup = types.InlineKeyboardMarkup(row_width=7)

    # Получаем год, месяц из выбранной даты
    year = selected_date.year
    month = selected_date.month

    # Создаем заголовок календаря
    header = [types.InlineKeyboardButton(text=translation_dict.get(month), callback_data="IGNORE")]
    markup.add(*header)

    # Создаем заголовки для дней недели
    week_days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    markup.add(*[types.InlineKeyboardButton(text=day, callback_data="IGNORE") for day in week_days])

    # Получаем матрицу дней месяца с учетом дней недели
    month_matrix = calendar.monthcalendar(year, month)

    # Добавляем кнопки календаря в разметку
    if month > datetime.now().month:
        for week in month_matrix[:2]:
            markup.add(*[types.InlineKeyboardButton(text=day, callback_data=f"{year}-{month}-{day}") if day != 0
                         else types.InlineKeyboardButton(text=" ", callback_data="IGNORE") for day in week])
    else:
        for week in month_matrix:
            markup.add(*[types.InlineKeyboardButton(text=day, callback_data=f"{year}-{month}-{day}") if day != 0
                         else types.InlineKeyboardButton(text=" ", callback_data="IGNORE") for day in week])
    # Добавляем кнопки для навигации между месяцами
    prev_month = selected_date - relativedelta(months=1)
    next_month = selected_date + relativedelta(months=1)
    if month.__int__() > datetime.now().month.__int__():
        markup.row(types.InlineKeyboardButton("предыдущий месяц", callback_data=f"PREV_MONTH:{prev_month}"))
    else:
        markup.row(types.InlineKeyboardButton("следующий месяц", callback_data=f"NEXT_MONTH:{next_month}"))
    return markup


# Обработчик команды /start
@bot.message_handler(commands=['start'])
def start(message):
    # Создаем клавиатуру с календарем на текущий месяц
    markup = create_keyboard_with_calendar(datetime.now())
    bot.send_message(message.chat.id, "Пожалуйста, выберите дату:", reply_markup=markup)


# Обработчик нажатия на кнопку с датой или навигации
@bot.callback_query_handler(func=lambda call: call.data != "IGNORE" and not call.data.startswith("hour:"))
def callback_query_data(call):
    data_parts = call.data.split(":", maxsplit=1)
    if len(data_parts) == 2:
        action, selected_date = call.data.split(":", maxsplit=1)
        selected_date = datetime.strptime(selected_date, "%Y-%m-%d %H:%M:%S.%f")
    else:
        # Обработка случая, когда в строке нет разделителя ":"
        action = None
        selected_date = datetime.strptime(call.data, "%Y-%m-%d")

    if action == "PREV_MONTH" or action == "NEXT_MONTH":
        # Создаем клавиатуру с календарем на предыдущий или следующий месяц
        markup = create_keyboard_with_calendar(selected_date)
        bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                      reply_markup=markup)

    elif action is None and selected_date > datetime.now():
        # Создаем клавиатуру с часами работы салона
        bot.edit_message_text("Выберите время для записи:", call.message.chat.id, call.message.message_id,
                              reply_markup=create_keyboard_with_hours())
    return f"{selected_date.strftime("%d-%m-%Y")}"


# Функция для создания клавиатуры с календарем на основе выбранной даты
def create_keyboard_with_hours():
    # Устанавливаем количество кнопок в строке клавиатуры = 7
    markup = types.InlineKeyboardMarkup(row_width=4)
    # Создаем заголовки для дней недели
    hours_list = [f"{hour}:00" for hour in range(10, 22)]
    markup.add(*[types.InlineKeyboardButton(text=hour, callback_data=f"hour:{hour}") for hour in hours_list])
    return markup


# Обработчик для кнопки с часом
@bot.callback_query_handler(func=lambda call: call.data.startswith("hour:"))
def callback_query_hour(call):
    hour = call.data.split(":")[1]  # Получаем час из callback-данных
    bot.edit_message_text("Введите свой номер телефона в формате: 9230001204", call.message.chat.id, call.message.message_id,
                          reply_markup=None)
    return f"{hour}:00"
