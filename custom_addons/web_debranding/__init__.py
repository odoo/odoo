# License MIT (https://opensource.org/licenses/MIT).

from . import models
from . import controllers
from . import translate

from odoo import SUPERUSER_ID, api

MODULE = "_web_debranding"


def uninstall_hook(cr):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["ir.model.data"]._module_data_uninstall([MODULE])
