from odoo.http import register_select_db_paths

from . import controllers
from . import models
from . import reports
from . import tools

register_select_db_paths("/odoo", "/web", "/web/login", prefixes=("/odoo/",))
