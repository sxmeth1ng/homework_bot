import logging
import os
import requests
import time
import sys

from dotenv import load_dotenv
from telebot import TeleBot

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)


PRACTICUM_TOKEN = os.getenv('practicum_token')
TELEGRAM_TOKEN = os.getenv('telegram_token')
TELEGRAM_CHAT_ID = os.getenv('chat_id')
RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


class ServerError(Exception):
    """Исключение для ошибок сервера Практикума."""


def check_tokens():
    """Проверка подгрузки токенов."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def send_message(bot, message):
    """Функция отправки сообщения ботом."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
        )
        logger.debug(f'Отправлено сообщение: {message}')
    except Exception:
        raise Exception('Не удалось отправить сообщение.')


def get_api_answer(current_timestamp):
    """Функция отвечающая за запрос к endpoint."""
    params = {'from_date': current_timestamp}
    req_params = dict(url=ENDPOINT, headers=HEADERS, params=params)
    try:
        response = requests.get(**req_params)
    except requests.exceptions.RequestException:
        raise ConnectionError('Ошибка запроса')
    if response.status_code != 200:
        raise ServerError('Ошибка со стороны сервера')
    response_json = response.json()
    server_errors = []
    for item in ('code', 'error'):
        if item in response_json:
            server_errors.append(f'{item} : {response_json[item]}')
    if server_errors:
        raise ServerError
    return response_json


def check_response(response):
    """Функция проверяющий ответ от API сервиса."""
    if not isinstance(response, dict):
        raise TypeError('Ответ API не является словарем.')
    hws = response.get('homeworks')
    cur_date = response.get('current_date')
    if (hws is None or cur_date is None):
        raise KeyError('Ошибка в получении значений словаря.')
    if not isinstance(hws, list):
        raise TypeError('Ответ API не соответствует ожиданиям.')
    return hws


def parse_status(homework):
    """Функция выводящая сообщения для бота."""
    homework_name = homework.get('homework_name')
    if not homework_name:
        raise KeyError(f'Отсутствует или пустое поле: {homework_name}')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_VERDICTS:
        raise KeyError(f'Неизвестный статус: {homework_status}')
    verdict = HOMEWORK_VERDICTS.get(homework_status)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Отсутствует переменная окружения')
        sys.exit()
    bot = TeleBot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if homeworks:
                message = parse_status(homeworks[0])
                send_message(bot, message)
            else:
                logger.debug('Новые статусы в ответе отсутствуют')
            current_timestamp = response.get(
                'current_date',
                int(time.time()) - RETRY_PERIOD
            )
        except Exception as error:
            logger.error(error)
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
