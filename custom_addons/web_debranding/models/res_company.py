# Copyright 2020 Ivan Yelizariev
# License OPL-1 (https://www.odoo.com/documentation/user/14.0/legal/licenses/licenses.html#odoo-apps).
from odoo import fields, models


class Company(models.Model):
    _inherit = "res.company"

    def _get_default_favicon(self, original=False):
        return None

    favicon = fields.Binary(default=_get_default_favicon)
