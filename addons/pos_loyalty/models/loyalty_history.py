# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class LoyaltyHistory(models.Model):
    _inherit = "loyalty.history"

    def _order_id_ondelete(self, model):
        if model._name == 'pos.order':
            return 'set null'
        return super()._order_id_ondelete(model)
