# Copyright 2018 Tecnativa - Jairo Llopis
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.models import Model, api
from odoo.tools.safe_eval import const_eval


class IrConfigParameter(Model):
    _inherit = "ir.config_parameter"

    @api.model
    def get_web_dialog_size_config(self):
        get_param = self.sudo().get_param
        return {
            "default_maximize": const_eval(
                get_param("web_dialog_size.default_maximize", "False")
            )
        }
