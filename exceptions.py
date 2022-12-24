class Not200HttpStatus(Exception):
    """Статут ответа от API отличный от 200."""

    pass


class UnknownHomeworkStatus(Exception):
    """Неизвестный статус в домашнем задании."""

    pass
