# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class LoyaltyCard(models.Model):
    _inherit = 'loyalty.card'

    order_id = fields.Many2one('sale.order', 'Order Reference', readonly=True,
        help="The sales order from which coupon is generated")

    def _get_default_template(self):
        default_template = super()._get_default_template()
        if not default_template:
            default_template = self.env.ref('loyalty.mail_template_loyalty_card', raise_if_not_found=False)
        return default_template

    def _get_mail_partner(self):
        return super()._get_mail_partner() or self.order_id.partner_id

    def _get_mail_author(self):
        """Default author is the order's salesperson if available, else the order's company."""
        if not self.order_id or self.order_id.sudo().company_id not in self.env.companies:
            return super()._get_mail_author()
        self.ensure_one()
        return (self.order_id.user_id or self.order_id.company_id).partner_id

    def _get_signature(self):
        return self.order_id.user_id.signature or super()._get_signature()

    def _compute_use_count(self):
        super()._compute_use_count()
        read_group_res = self.env['sale.order.line']._read_group(
            [('coupon_id', 'in', self.ids)], ['id'], ['coupon_id'])
        count_per_coupon = {r['coupon_id'][0]: r['coupon_id_count'] for r in read_group_res}
        for card in self:
            card.use_count += count_per_coupon.get(card.id, 0)

    def _has_source_order(self):
        return super()._has_source_order() or bool(self.order_id)
