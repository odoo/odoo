# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class LoyaltyHistory(models.Model):
    _inherit = "loyalty.history"

    def _order_id_ondelete(self, model):
        if model._name == 'sale.order':
            return 'set null'
        return super()._order_id_ondelete(model)

    def _get_order_portal_url(self):
        if self.order_id and self.order_model == "sale.order":
            return self.env["sale.order"].browse(self.order_id).get_portal_url()
        return super()._get_order_portal_url()
