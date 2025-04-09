# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class LoyaltyReward(models.Model):
    _inherit = 'loyalty.reward'

    def _get_discount_product_values(self):
        res = super()._get_discount_product_values()
        for vals in res:
            vals.update({
                'supplier_taxes_id': False,
                'invoice_policy': 'order',
            })
        return res

    def unlink(self):
        if len(self) == 1 and self.env['sale.order.line'].sudo().search_count([('reward_id', 'in', self.ids)], limit=1):
            return self.action_archive()
        return super().unlink()
