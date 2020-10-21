import requests
import time
import json
import telegram
import logging
from database import Database
from multiprocessing import Process

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

def notify(userId, slug, rest_name, rest_link):
    bot.send_message(chat_id=userId, parse_mode=telegram.ParseMode.HTML,
        text=f"""Hey there,
{rest_name} is now ONLINE!!! Enjoy :)

<b><a href="{rest_link}">Click here to order from {rest_name}</a></b>
&#8204;
        """) ## &#8204; - zero-width non-joiner (ZWNJ)
    db = Database()
    db.removeNotification(userId=userId, slug=slug, reason="Notified")
    db.close()

def check_restaurant(slug, notifications):
    result = requests.get(f"{wolt_api}/{slug}").json()["results"][0]
    is_online = result["online"]
    if is_online:
        try:
            rest_name = list(filter(lambda x: x["lang"] == "en", result["name"]))[0]["value"]
        except:
            rest_name = list(filter(lambda x: x["lang"] == "he", result["name"]))[0]["value"]
        
        rest_link = result["public_url"]
        users2Notify = set(map(lambda x: x["userId"], filter(lambda x: x["slug"] == slug, notifications)))
        notifiers = [Process(target=notify, args=(user, slug, rest_name, rest_link)) for user in users2Notify]

        for notifier in notifiers:
            notifier.start()

def main():
    db = Database()
    notifications = db.getAllActiveNotifications()
    db.close()
    uniqueSlugs = set(map(lambda x: x["slug"], notifications))
    rest_checkers = [Process(target=check_restaurant, args=(slug, notifications)) for slug in uniqueSlugs]

    for rest_checker in rest_checkers:
        rest_checker.start()
        

if __name__ == '__main__':
    wolt_api = "https://restaurant-api.wolt.com/v3/venues/slug"
    telegram_bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    bot = telegram.Bot(token=telegram_bot_token)

    while True:
        main()
        time.sleep(10)
        