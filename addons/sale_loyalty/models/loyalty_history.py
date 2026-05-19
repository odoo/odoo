# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class LoyaltyHistory(models.Model):
    _inherit = "loyalty.history"

    def _res_model_check_model(self, model_name):
        return model_name == 'sale.order' or super()._res_model_check_model(model_name)

    def _get_order_portal_url(self):
        if self.order_id and self.order_model == "sale.order":
            return self.env["sale.order"].browse(self.order_id).get_portal_url()
        return super()._get_order_portal_url()
