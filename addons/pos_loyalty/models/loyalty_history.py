# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class LoyaltyHistory(models.Model):
    _inherit = "loyalty.history"

    def _res_model_check_model(self, model_name):
        return model_name == 'pos.order' or super()._res_model_check_model(model_name)
