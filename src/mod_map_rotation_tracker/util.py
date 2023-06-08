from functools import wraps
from mod_logging import LOG_CURRENT_EXCEPTION


def safe_callback(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception:
            LOG_CURRENT_EXCEPTION()

    return wrapper
