import logging
import os
import requests
import time
import sys
from http import HTTPStatus

from dotenv import load_dotenv
from telebot import TeleBot, apihelper

from exceptions import ServerError

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(stream=sys.stdout)
formatter = logging.Formatter(
    '%(funcName)s - %(asctime)s - %(name)s - %(levelname)s - %(message)s'
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


def check_tokens():
    """Проверка подгрузки токенов."""
    SOURCE = ('PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID')
    missing_tokens = []
    for token in SOURCE:
        if not globals()[token]:
            missing_tokens.append('token')
    if missing_tokens:
        message = ', '.join(missing_tokens)
        logger.critical(f'Ошибка токенов - {message}')
        sys.exit(1)


def send_message(bot, message):
    """Функция отправки сообщения ботом."""
    logger.info('Отправка сообщения')
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
        )
        logger.debug(f'Отправлено сообщение: {message}')
    except (apihelper.ApiException, requests.RequestException) as error:
        logger.error(error)
    logger.info('Сообщение отправлено')


def get_api_answer(current_timestamp):
    """Функция отвечающая за запрос к endpoint."""
    params = {'from_date': current_timestamp}
    req_params = dict(url=ENDPOINT, headers=HEADERS, params=params)
    try:
        logger.info(
            f'Производится запрос к API - {ENDPOINT}, с параметрами - {params}'
        )
        response = requests.get(**req_params)
    except requests.exceptions.RequestException:
        raise ConnectionError(
            f'Ошибка запроса к API - {ENDPOINT}, с параметрами - {params}'
        )
    if response.status_code != HTTPStatus.OK:
        raise ServerError(
            f'Ошибка со стороны сервера,возвращённый ответ - {response.reason}'
            f'Статус код - {response.status_code}.'
        )
    logger.info('Запрос к API прошёл успешно.')
    return response.json()


def check_response(response):
    """Функция проверяющий ответ от API сервиса."""
    logger.info('Начало проверки ответа сервера.')
    if not isinstance(response, dict):
        raise TypeError(
            f'Ответ API является - {type(response)}, а не словарём.'
        )
    if 'homeworks' not in response:
        raise KeyError('Ошибка в получении значения homeworks в словаре.')
    hws = response.get('homeworks')
    if not isinstance(hws, list):
        raise TypeError(
            f'Ответ API является - {type(hws)}, а не списком.'
        )
    logger.info('Проверка ответа сервера прошла успешно.')
    return hws


def parse_status(homework):
    """Функция выводящая сообщения для бота."""
    logger.info('Начало проверки статуса работы.')
    if 'homework_name' not in homework:
        raise KeyError('Отсутствует поле: homework_name')
    homework_name = homework.get('homework_name')
    if 'status' not in homework:
        raise KeyError('Ошибка в получение ключа status из словаря.')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_VERDICTS:
        raise KeyError(f'Неизвестный статус: {homework_status}')
    verdict = HOMEWORK_VERDICTS.get(homework_status)
    logger.info('Проверка статуса прошла успешно.')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = TeleBot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    last_message = None
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if homeworks:
                message = parse_status(homeworks[0])
                send_message(bot, message)
                last_message = message
            else:
                logger.debug('Новые статусы в ответе отсутствуют')
            current_timestamp = response.get(
                'current_date',
                int(time.time())
            )
        except Exception as error:
            logger.error(error)
            message = f'Сбой в работе программы: {error}'
            if last_message != message:
                send_message(bot, message)
                last_message = message
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
