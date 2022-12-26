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


logger = logging.getLogger('logger')
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())
handler = logging.StreamHandler(stream=sys.stdout)
handler.setFormatter(logging.Formatter(fmt='[%(asctime)s: %(levelname)s]'))
logger.addHandler(handler)
logger.debug('Бот ожил!')


def check_tokens():
    """Функция проверки доступности переменных окружения."""
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))


def send_message(bot, message):
    """Функция отправки сообщения."""
    logger.debug('Попытка отправки сообщения')
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug(f'Отправлено сообщение: {message}')
    except Exception as error:
        logger.error(f'Сообщение не отправлено: {error}')


def get_api_answer(timestamp):
    """Функция запроса к эндпоинту API-сервиса."""
    logger.debug('Попытка запроса к эндпоинту API-сервиса')
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
    raise exceptions.Not200HttpStatus


def check_response(response):
    """Функция проверяет ответ API на соответствие документации."""
    if not isinstance(response, dict):
        raise TypeError('Неверный тип response. Ожидается словарь.')
    homeworks = response.get('homeworks')
    if 'homeworks' not in response:
        raise KeyError('Ключ homeworks отсутствует в response')
    if 'current_date' not in response:
        raise KeyError('Ключ current_date отсутствует в response')
    if not isinstance(homeworks, list):
        raise TypeError('Неверный тип homeworks. Ожидается список.')
    return homeworks


def parse_status(homework):
    """Функция проверяет статус домашнего задания."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if 'homework_name' not in homework:
        raise KeyError('Ключ homeworks отсутствует в homework')
    if 'status' not in homework:
        raise KeyError('Ключ status отсутствует в homework')
    if homework_status not in HOMEWORK_VERDICTS:
        raise exceptions.UnknownHomeworkStatus
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        message = 'Недоступна одна или несколько переменных окружения.'
        logger.critical(message)
        sys.exit(message)
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if homeworks:
                message = parse_status(homeworks[0])
                send_message(bot, message)
            else:
                logger.info(
                    f'Изменений в статусе нет, ждём {RETRY_PERIOD} секунд')
            timestamp = int(time.time())
        except Exception as error:
            message = f'Бот сломался: {error}'
            logger.error(message)
            send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
