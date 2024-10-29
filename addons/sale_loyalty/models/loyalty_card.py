# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class LoyaltyCard(models.Model):
    _inherit = ['loyalty.card']

    order_id = fields.Many2one(
        comodel_name='sale.order',
        string="Order Reference",
        readonly=True,
        help="The sales order from which coupon is generated")
    order_id_partner_id = fields.Many2one(
        'res.partner', 'Sale Order Customer',
        related='order_id.partner_id')

    def _get_default_template(self):
        default_template = super()._get_default_template()
        if not default_template:
            default_template = self.env.ref('loyalty.mail_template_loyalty_card', raise_if_not_found=False)
        return default_template

    def _mail_get_partner_fields(self, introspect_fields=False):
        return super()._mail_get_partner_fields(introspect_fields=introspect_fields) + ['order_id_partner_id']

    def _get_signature(self):
        return self.order_id.user_id.signature or super()._get_signature()

    def _compute_use_count(self):
        super()._compute_use_count()
        read_group_res = self.env['sale.order.line']._read_group(
            [('coupon_id', 'in', self.ids)], ['coupon_id'], ['__count'])
        count_per_coupon = {coupon.id: count for coupon, count in read_group_res}
        for card in self:
            card.use_count += count_per_coupon.get(card.id, 0)

    def _has_source_order(self):
        return super()._has_source_order() or bool(self.order_id)
