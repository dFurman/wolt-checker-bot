import requests
import json
import csv
import telegram
from telegram import (InlineKeyboardButton, InlineKeyboardMarkup)
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters,
                          ConversationHandler, CallbackQueryHandler)
import logging
from database import Database
import os
from multiprocessing import Process

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

SEARCH, CHECKER = range(2)

def start(update, context):
    userId = update.message.from_user.id
    userName = update.message.from_user.name
    update.message.reply_text(f"""
Hello :)
Please Enter the restaurant name you want to check.
It can be in English/Hebrew.
To show current notification registrations please write: /show
""")
    return SEARCH

def search_restaurant(update, context):
    bot.send_chat_action(chat_id=update.message.chat_id, action=telegram.ChatAction.TYPING)
    wolt_api = "https://restaurant-api.wolt.com/v1"
    query = update.message.text
        
    results = requests.get(f"{wolt_api}/search?sort=relevancy&q={query}").json()["results"]
    button_list = []
    rest_name = None
    if results:
        for result in results[:10]:
            try:
                rest_name = list(filter(lambda x: x["lang"] == "he", result["value"]["name"]))[0]["value"]
            except:
                rest_name = list(filter(lambda x: x["lang"] == "en", result["value"]["name"]))[0]["value"]

            button_list.append(
                [
                    InlineKeyboardButton(rest_name, callback_data=result["value"]["slug"])
                ]
            )
        reply_markup = InlineKeyboardMarkup(button_list)

        update.message.reply_text("Please Select the wanted restaurant", reply_markup=reply_markup)
    else:
        update.message.reply_text("I'm Sorry! No restaurants were found.\n\
you can search for another one if you like.")

    return CHECKER

def checker_query_handler(update, context):
    wolt_api = "https://restaurant-api.wolt.com/v3/venues/slug"
    query = update.callback_query
    query.answer()
    
    slug = query.data
    userId = update.callback_query.from_user["id"]

    result = requests.get(f"{wolt_api}/{slug}").json()["results"][0]
    try:
        rest_name = list(filter(lambda x: x["lang"] == "en", result["name"]))[0]["value"]
    except:
        rest_name = list(filter(lambda x: x["lang"] == "he", result["name"]))[0]["value"]
        
    is_online = result["online"]
    rest_link = result["public_url"]
    if is_online:
        query.edit_message_text(parse_mode=telegram.ParseMode.HTML,
        text=f"{rest_name} is OPEN :)\n\n\
<b><a href='{rest_link}'>Click here to order from {rest_name}</a></b>\n\n\
Thank you for using Wolt Checker Bot :)\n\
To re-run the bot, please write /start")
        return cancel(update, context)
    else:
        button_list = [
            [InlineKeyboardButton("Yes", callback_data=f"REGISTER_{slug}_{rest_name}")],
            [InlineKeyboardButton("No", callback_data=f"NO")],

        ]
        reply_markup = InlineKeyboardMarkup(button_list)

        query.edit_message_text(f"{rest_name} is CLOSED :(\n\n\
Do you want to register for an update when the restaurant will be open again ?",
        reply_markup=reply_markup)

        return SEARCH

def register_handling(update, context):
    query = update.callback_query
    query.answer()
    
    data = query.data.split("_")
    action = data[0]
    
    if action == "NO":
        query.edit_message_text("Thank you for using Wolt Checker Bot :)\n\n\
To re-run the bot, please write /start")
        return ConversationHandler.END

    if action == "REMOVE":
        userId = update.callback_query.from_user["id"]
        slug = data[1]
        db = Database()
        db.removeNotification(userId=userId, slug=slug, reason="UserManually")
        db.close()
        query.edit_message_text("No Problem, you are removed from being notified.")
        
    if action == "REGISTER":
        userId = update.callback_query.from_user["id"]
        slug = data[1]
        rest_name = "_".join(data[2:])

        Process(target=addNewNotification, args=(userId, slug)).start()
        
        query.edit_message_text(f"No Problem, you will be notified once {rest_name} is open.\n\n\
Thank you for using Wolt Checker Bot :)\n\n\
To re-run the bot, please write /start")
        
        return ConversationHandler.END

def addNewNotification(userId, slug):
    db = Database()
    db.addNewNotification(userId=userId, slug=slug)
    db.close()

def list_registrations(update, context):
    wolt_api = "https://restaurant-api.wolt.com/v3/venues/slug"
    userId = update.message.chat_id
    db = Database()
    relevant = db.getUserActiveNotifications(userId=userId)
    db.close()
    if not relevant:
        update.message.reply_text("You are not registered for any notification right now.")
        return cancel(update, context)

    for slug in set(relevant):
        button_list = [
            [InlineKeyboardButton("Remove", callback_data=f"REMOVE_{slug}")]
        ]
        result = requests.get(f"{wolt_api}/{slug}").json()["results"][0]
        try:
            rest_name = list(filter(lambda x: x["lang"] == "en", result["name"]))[0]["value"]
        except:
            rest_name = list(filter(lambda x: x["lang"] == "he", result["name"]))[0]["value"]

        reply_markup = InlineKeyboardMarkup(button_list)
        update.message.reply_text(rest_name, reply_markup=reply_markup)


def cancel(update, context):
    try:
        update.message.reply_text("Thank you for using Wolt Checker Bot :)\n\n\
To re-run the bot, please write /start")
    except:
        pass
    return ConversationHandler.END

def main():
    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # Post version 12 this will no longer be necessary
    updater = Updater(telegram_bot_token, use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],

        states={
            SEARCH: [
                        CommandHandler('show', list_registrations),
                        CommandHandler('start', start),
                        MessageHandler(Filters.text, search_restaurant),
                        CallbackQueryHandler(register_handling)
                    ],
            CHECKER: [
                        CallbackQueryHandler(checker_query_handler),
                        CommandHandler('show', list_registrations),
                        CommandHandler('start', start),
                        MessageHandler(Filters.text, search_restaurant)
                    ]
        },

        fallbacks=[CommandHandler('cancel', cancel)]
    )

    dp.add_handler(conv_handler)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    telegram_bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    bot = telegram.Bot(token=telegram_bot_token)
    main()