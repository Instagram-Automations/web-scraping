import logging
import os
from typing import Optional

_LOGGERS = {}


def get_logger(name: Optional[str] = None) -> logging.Logger:
    if name in _LOGGERS:
        return _LOGGERS[name]

    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logger = logging.getLogger(name if name else "app")
    logger.setLevel(level)
    if not logger.handlers:
        ch = logging.StreamHandler()
        ch.setLevel(level)
        fmt = logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s", "%Y-%m-%d %H:%M:%S")
        ch.setFormatter(fmt)
        logger.addHandler(ch)
        logger.propagate = False
    _LOGGERS[name] = logger
    return logger
