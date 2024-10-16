# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons import loyalty


class LoyaltyHistory(loyalty.LoyaltyHistory):

    def _get_order_portal_url(self):
        if self.order_id and self.order_model == 'sale.order':
            return self.env['sale.order'].browse(self.order_id).get_portal_url()
        return super()._get_order_portal_url()
