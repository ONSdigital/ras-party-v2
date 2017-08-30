from json import loads

import structlog
from ras_common_utils.ras_config import ras_config
from ras_common_utils.ras_logger.ras_logger import configure_logger

from run import create_app, initialise_db

"""
This is a duplicate of run.py, with minor modifications to support gunicorn execution.
"""

logger = structlog.get_logger()


config_path = 'config/config.yaml'
with open(config_path) as f:
    config = ras_config.from_yaml_file(config_path)

app = create_app(config)
with open(app.config['PARTY_SCHEMA']) as io:
    app.config['PARTY_SCHEMA'] = loads(io.read())
configure_logger(app.config)
logger.debug("Created Flask app.")

initialise_db(app)

scheme, host, port = app.config['SCHEME'], app.config['HOST'], int(app.config['PORT'])
