from functools import wraps

import structlog
from flask import make_response, jsonify, current_app

from swagger_server.controllers.ras_error import RasError

log = structlog.get_logger()


def translate_exceptions(f):
    # TODO: ultimately we don't want to expose error details to the caller, so should possible map expected
    # TODO: errors to something more friendly, and fall back to a generic 500 on unexpected errors
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            # TODO: log the stack-trace
            log.error(str(e))
            if current_app.config.feature.translate_exceptions:
                raise RasError(str(e))
            else:
                raise
    return wrapper
