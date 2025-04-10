from flask import Blueprint

api_blueprint = Blueprint('api', __name__)

from . import routes_info
from . import routes_data
from . import routes_update_conf