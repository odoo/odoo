# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import SUPERUSER_ID, api


def enable_multi_locations(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    ResConfig = env["res.config.settings"]
    default_values = ResConfig.default_get(list(ResConfig.fields_get()))
    default_values.update({"group_stock_multi_locations": True})
    ResConfig.create(default_values).execute()
