import os
import requests
import time

from dotenv import load_dotenv
from telebot import TeleBot

load_dotenv()


PRACTICUM_TOKEN = os.getenv('practicum_token')
TELEGRAM_TOKEN = os.getenv('telegram_token')
TELEGRAM_CHAT_ID = os.getenv('chat_id')
print(PRACTICUM_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_TOKEN)
RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    if PRACTICUM_TOKEN and TELEGRAM_CHAT_ID and TELEGRAM_TOKEN:
        return True
    else:
        pass


def send_message(bot, message):
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)


def get_api_answer(timestamp):
    homework = requests.get(
        ENDPOINT,
        headers=HEADERS, 
        params={'from_date': timestamp}
    )
    return homework.json()


def check_response(response):
    if response.get('homeworks') is not None:
        if len(response.get('homeworks')) > 0:
            return True
    return False


def parse_status(homework):
    homework = homework.get('homeworks')[0]
    homework_name = homework['homework_name']
    status = homework['status']
    verdict = HOMEWORK_VERDICTS[status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""


    # Создаем объект класса бота
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    homework = get_api_answer(timestamp)
    if check_response(homework):
        send_message(bot, parse_status(homework))
    # while True:
    #     try:

    #         ...

    #     except Exception as error:
    #         message = f'Сбой в работе программы: {error}'
    #         ...
    #     ...


if __name__ == '__main__':

    main()
