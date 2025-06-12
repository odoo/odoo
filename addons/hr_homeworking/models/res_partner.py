# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _store_main_user_id_default_fields(self):
        return super()._store_main_user_id_default_fields() + ["remote_work_location_type"]
