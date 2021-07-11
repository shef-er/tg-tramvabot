#!/usr/bin/env python
# pylint: disable=W0613, C0116

import logging
from functools import wraps
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ChatAction, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext

import ettu_api
from config import TOKEN


GREETING_HELP = "Введите /start или /search чтобы узнать где ваш трамвай"
GREETING_LETTER_BUTTONS = "Выберите первый символ названия станции:"
GREETING_STATION_BUTTONS = "Выберите станцию и направление (символ %s):"

ERROR_TRY_LATER = "Произошла ошибка, попробуйте снова позже"
TEXT_NO_RESULTS = "Результатов не найдено"

BUTTON_RETRY = "✅ Новый поиск"
BUTTON_REFRESH = "🔄 Обновить"
BUTTON_BACK = "↩️ Назад"

TEXT_RESULT_ROW_PREFIX = "Трамвай №"

COMMAND_BACK = "BACK"

station_letters_list = [
    ["1", "4", "7", "А", "Б", "В", "Г", "Д", ],
    ["Е", "Ж", "З", "И", "К", "Л", "М", "Н", ],
    ["О", "П", "Р", "С", "T", "У", "Ф", "Х", ],
    ["Ц", "Ч", "Ш", "Щ", "Э", "Ю", "Я", ],
]


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)


def send_action(action):
    """Sends `action` while processing func command."""

    def decorator(func):
        @wraps(func)
        def command_func(update, context, *args, **kwargs):
            context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=action)
            return func(update, context, *args, **kwargs)

        return command_func

    return decorator


def build_letter_buttons() -> list:
    letter_buttons = list()
    for letters in station_letters_list:
        buttons = list(map(
            lambda button: InlineKeyboardButton(button, callback_data=button),
            letters
        ))
        letter_buttons.append(buttons)

    return letter_buttons


def build_station_buttons_by_first_letter(letter: str) -> list:
    response = ettu_api.get_stations_by_first_letter(letter)
    if response['error'] or not response['payload']:
        return []

    stations = response['payload']

    logging.info(str(stations));

    station_buttons = list(map(
        lambda station: [
            InlineKeyboardButton(station['name'], callback_data=station['code'])
        ],
        stations
    ))

    return station_buttons


def build_result_by_station_code(code: str) -> str:
    response = ettu_api.get_car_timings_by_station_code(code)
    if response['error']:
        return ERROR_TRY_LATER
    
    station_name = response['payload']['station']
    time = response['payload']['time']
    cars = response['payload']['cars']
    
    result_list = [
        "%s %s" % (station_name, time),
        "",
    ]
    
    if not cars:
        result_list.append(TEXT_NO_RESULTS)
    else:
        for car in cars:
            number = car['number']
            time = car['time']
            distance = car['distance']

            result_list.append("%s%-4s %7s %6s" % (TEXT_RESULT_ROW_PREFIX, "%s," % number, "%s," % time, distance))

    return "\n".join(result_list)


def start_command(update: Update, context: CallbackContext) -> None:
    search_command(update, context)


@send_action(ChatAction.TYPING)
def search_command(update: Update, context: CallbackContext) -> None:
    keyboard_buttons = build_letter_buttons()
    reply_markup = InlineKeyboardMarkup(keyboard_buttons)

    update.message.reply_text(
        GREETING_LETTER_BUTTONS,
        reply_markup=reply_markup
    )


@send_action(ChatAction.TYPING)
def button_command(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()

    if query.data == COMMAND_BACK:
        keyboard_buttons = build_letter_buttons()
        reply_markup = InlineKeyboardMarkup(keyboard_buttons)

        query.edit_message_text(
            text=GREETING_LETTER_BUTTONS,
            reply_markup=reply_markup
        )
    elif len(query.data) == 1:
        keyboard_buttons = build_station_buttons_by_first_letter(query.data)
        keyboard_buttons.append([InlineKeyboardButton(BUTTON_BACK, callback_data=COMMAND_BACK)])
        reply_markup = InlineKeyboardMarkup(keyboard_buttons)

        message = TEXT_NO_RESULTS
        if keyboard_buttons:
            message = GREETING_STATION_BUTTONS % query.data

        query.edit_message_text(
            text=message,
            reply_markup=reply_markup
        )
    elif query.data:
        keyboard_buttons = list()
        keyboard_buttons.append([InlineKeyboardButton(BUTTON_REFRESH, callback_data=query.data)])
        keyboard_buttons.append([InlineKeyboardButton(BUTTON_RETRY, callback_data=COMMAND_BACK)])
        reply_markup = InlineKeyboardMarkup(keyboard_buttons)

        result = build_result_by_station_code(query.data)
        message = "```\n%s\n```" % result

        query.edit_message_text(
            text=message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN_V2
        )
    else:
        query.edit_message_text(text=GREETING_HELP)


@send_action(ChatAction.TYPING)
def help_command(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(GREETING_HELP)


def main():
    updater = Updater(TOKEN, use_context=True)

    updater.dispatcher.add_handler(CommandHandler('start', start_command))
    updater.dispatcher.add_handler(CommandHandler('search', search_command))
    updater.dispatcher.add_handler(CallbackQueryHandler(button_command))
    updater.dispatcher.add_handler(CommandHandler('help', help_command))

    updater.start_polling()

    # Run the bot until the user presses Ctrl-C or the process receives SIGINT, SIGTERM or SIGABRT
    updater.idle()


if __name__ == '__main__':
    main()
