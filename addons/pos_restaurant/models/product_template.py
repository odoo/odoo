# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.model
    def default_get(self, fields):
        defaults = super().default_get(fields)
        if "is_storable" in fields:
            session_id = self.env.context.get("pos_session_id")
            if session_id:
                session = self.env["pos.session"].browse(session_id)
                if session.config_id.module_pos_restaurant:
                    defaults["is_storable"] = False
        return defaults
