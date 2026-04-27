# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _recompute_taxes(self):
        super()._recompute_taxes()
        if self.env.context.get('is_express_checkout_flow'):
            self._get_and_set_external_taxes_on_eligible_records()
