# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import os

from odoo import api, fields, models


class LoyaltyCard(models.Model):
    _inherit = 'loyalty.card'

    order_id = fields.Many2one(
        comodel_name='sale.order',
        string="Order Reference",
        readonly=True,
        help="The sales order from which coupon is generated")

    history_ids = fields.One2many(
        comodel_name='sale.loyalty.history',
        inverse_name='coupon_id',
        ondelete='cascade',
    )

    # TODO: MATP Not use and probably not the best way :/ => check STOCK APP
    barcode = fields.Char(
        string='Barcode',
        default=lambda self: str(int.from_bytes(os.urandom(8), 'little')),
        readonly=True,
        copy=False
    )

    @api.model_create_multi
    def create(self, vals_list):
        coupons = super().create(vals_list)
        for coupon in coupons:
            if coupon.points:
                coupon.history_ids = self.env['sale.loyalty.history'].create({
                    'description': vals_list['description'],
                    'coupon_id': coupon.id,
                    'sale_order_id': coupon.order_id.id,
                    'sale_order_name': coupon.order_id.name,
                    'issued': coupon.points,
                    'new_balance': coupon.points,
                })
        return coupons

    def _get_default_template(self):
        default_template = super()._get_default_template()
        if not default_template:
            default_template = self.env.ref('loyalty.mail_template_loyalty_card', raise_if_not_found=False)
        return default_template

    def _get_mail_partner(self):
        return super()._get_mail_partner() or self.order_id.partner_id

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
