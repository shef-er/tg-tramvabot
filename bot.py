#!/usr/bin/env python
# pylint: disable=W0613, C0116

import logging
import requests
from lxml import html
from functools import wraps

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ChatAction, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext

from config import TOKEN


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)


GREETING_HELP = "Введите /start или /search чтобы узнать где ваш трамвай"
GREETING_LETTER_BUTTONS = "Выберите первый символ названия станции на которой находитесь:"
GREETING_STATION_BUTTONS = "Выберите станцию и направление (символ %s):"

TEXT_RETRY = "Повторить поиск"
TEXT_BACK = "Назад"
TEXT_NO_RESULTS = "Результатов не найдено"
TEXT_RESULT_ROW_PREFIX = "Трамвай №"
TEXT_TRY_LATER = "Произошла ошибка, попробуйте снова позже"

COMMAND_BACK = "BACK"


def send_action(action):
    """Sends `action` while processing func command."""

    def decorator(func):
        @wraps(func)
        def command_func(update, context, *args, **kwargs):
            context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=action)
            return func(update, context, *args, **kwargs)

        return command_func

    return decorator


def get_letter_buttons() -> list:
    letters_list = [
        ["1", "4", "7", "А", "Б", "В", "Г", "Д", ],
        ["Е", "Ж", "З", "И", "К", "Л", "М", "Н", ],
        ["О", "П", "Р", "С", "T", "У", "Ф", "Х", ],
        ["Ц", "Ч", "Ш", "Щ", "Э", "Ю", "Я", ],
    ]

    letter_buttons = list()
    for letters in letters_list:
        buttons = list(map(
            lambda button: InlineKeyboardButton(button, callback_data=button),
            letters
        ))
        letter_buttons.append(buttons)

    return letter_buttons


def get_station_buttons_by_first_letter(letter: str) -> list:
    response = requests.get("https://mobile.ettu.ru/stations/%s" % letter).text
    if not response:
        return []

    tree = html.fromstring(response)
    links = tree.xpath("//div")[0].xpath("./a[@href]")
    if len(links) == 0:
        return []

    station_buttons = list(map(
        lambda link: [InlineKeyboardButton(link.text, callback_data=link.attrib['href'].rsplit('/', 1)[-1])],
        links
    ))

    return station_buttons


def get_result_by_station(station: str) -> str:
    station = station.rsplit('/', 1)[-1]
    response = requests.get("https://mobile.ettu.ru/station/%s" % station).text
    if not response:
        return TEXT_TRY_LATER

    tree = html.fromstring(response)
    results_div = tree.xpath("//div")[0]

    station_name = results_div.xpath("./p")[0].text.strip()
    time = results_div.xpath("./p")[0].xpath("./b")[0].text.strip()

    result = [
        "%s %s" % (station_name, time),
        "",
    ]

    timings = results_div.xpath("./div")

    if len(timings) == 0:
        result.append(TEXT_NO_RESULTS)
    else:
        timings.pop(-1)
        for timing in timings:
            divs = timing.xpath("./div")

            number = divs[0].xpath("./b")[0].text.strip()
            time = divs[1].text.strip()
            distance = divs[2].text.strip()

            result.append("%s%-4s %7s %6s" % (TEXT_RESULT_ROW_PREFIX, "%s," % number, "%s," % time, distance))

    return "\n".join(result)


def start_command(update: Update, context: CallbackContext) -> None:
    search_command(update, context)


@send_action(ChatAction.TYPING)
def search_command(update: Update, context: CallbackContext) -> None:
    keyboard_buttons = get_letter_buttons()
    reply_markup = InlineKeyboardMarkup(keyboard_buttons)

    update.message.reply_text(
        GREETING_LETTER_BUTTONS,
        reply_markup=reply_markup
    )


def button_command(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()

    if query.data == COMMAND_BACK:
        keyboard_buttons = get_letter_buttons()
        reply_markup = InlineKeyboardMarkup(keyboard_buttons)

        query.edit_message_text(
            text=GREETING_LETTER_BUTTONS,
            reply_markup=reply_markup
        )
    elif len(query.data) == 1:
        context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=ChatAction.TYPING)
        keyboard_buttons = get_station_buttons_by_first_letter(query.data)
        keyboard_buttons.append([InlineKeyboardButton(TEXT_BACK, callback_data=COMMAND_BACK)])
        reply_markup = InlineKeyboardMarkup(keyboard_buttons)

        message = TEXT_NO_RESULTS
        if keyboard_buttons:
            message = GREETING_STATION_BUTTONS % query.data

        query.edit_message_text(
            text=message,
            reply_markup=reply_markup
        )
    elif query.data:
        context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=ChatAction.TYPING)
        keyboard_buttons = list()
        keyboard_buttons.append([InlineKeyboardButton(TEXT_RETRY, callback_data=COMMAND_BACK)])
        reply_markup = InlineKeyboardMarkup(keyboard_buttons)

        result = get_result_by_station(query.data)
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
