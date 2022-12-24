import logging
import os
import time
import sys
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

import exceptions

load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


# logging.basicConfig(
#     level=logging.DEBUG,
#     format='%(asctime)s, %(levelname)s, %(message)s, %(name)s',
# )
logger = logging.getLogger('logger')
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())
handler = logging.StreamHandler(stream=sys.stdout)
handler.setFormatter(logging.Formatter(
    fmt='[%(asctime)s: %(levelname)s]'))
logger.addHandler(handler)
logger.debug('Бот ожил!')


def check_tokens():
    """Функция проверки доступности переменных окружения."""
    tokens = {
        'practicum_token': PRACTICUM_TOKEN,
        'telegram_token': TELEGRAM_TOKEN,
        'telegram_chat_id': TELEGRAM_CHAT_ID,
    }
    for key, value in tokens.items():
        if value is None:
            logger.critical(f'{key} не найден, работа прервана')
            return False
    return True


def send_message(bot, message):
    """Функция отправки сообщения."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug(f'Отправлено сообщение: {message}')
    except Exception as error:
        logger.error(f'Сообщение не отправлено: {error}')


def get_api_answer(timestamp):
    """Функция запроса к эндпоинту API-сервиса."""
    try:
        params = {'from_date': timestamp}
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params
        )
        response_content = response.json()
    except requests.RequestException as error:
        raise Exception(
            f"При обработке запроса возникла исключительная ситуация: {error}"
        )
    if response.status_code == HTTPStatus.OK:
        return response_content
    else:
        logger.error('Ошибка в обращении к эндпоинту API-сервиса')
        raise exceptions.Not200HttpStatus


def check_response(response):
    """Функция проверяет ответ API на соответствие документации."""
    try:
        timestamp = response['current_date']
    except KeyError:
        logger.error('Ключ current_date отсутствует в response')
    try:
        homeworks = response['homeworks']
    except KeyError:
        logger.error('Ключ homeworks отсутствует в response')
    if isinstance(timestamp, int) and isinstance(homeworks, list):
        return homeworks
    else:
        raise TypeError


def parse_status(homework):
    """Функция проверяет статус домашнего задания."""
    try:
        homework_name = homework['homework_name']
    except KeyError:
        logger.error('Ключ homework_name отсутствует')
    homework_status = homework.get('status')
    if homework_status in HOMEWORK_VERDICTS:
        verdict = HOMEWORK_VERDICTS.get(homework_status)
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    else:
        raise exceptions.UnknownHomeworkStatus


def main():
    """Основная логика работы бота."""
    if check_tokens():
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
        timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            all_works = len(homeworks)
            while all_works > 0:
                message = parse_status(homeworks[all_works - 1])
                send_message(bot, message)
                all_works -= 1
            timestamp = int(time.time())
            logger.info(f'Изменений в статусе нет, ждём {RETRY_PERIOD} секунд')
            time.sleep(RETRY_PERIOD)
        except Exception as error:
            message = f'Бот сломался: {error}'
            send_message(bot, message)
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
