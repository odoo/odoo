# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class LoyaltyCard(models.Model):
    _name = 'loyalty.card'
    _inherit = ['loyalty.card', 'pos.load.mixin']

    source_pos_order_id = fields.Many2one('pos.order', "PoS Order Reference",
        help="PoS order where this coupon was generated.")
    source_pos_order_partner_id = fields.Many2one(
        'res.partner', "PoS Order Customer",
        related="source_pos_order_id.partner_id")

    @api.model
    def _load_pos_data_domain(self, data, config):
        return False

    @api.model
    def _load_pos_data_fields(self, config):
        return ['partner_id', 'code', 'points', 'program_id', 'expiration_date', 'write_date']

    def _has_source_order(self):
        return super()._has_source_order() or bool(self.source_pos_order_id)

    def _get_default_template(self):
        self.ensure_one()
        if self.source_pos_order_id:
            return self.env.ref('pos_loyalty.mail_coupon_template', False)
        return super()._get_default_template()

    def _mail_get_partner_fields(self, introspect_fields=False):
        return super()._mail_get_partner_fields(introspect_fields=introspect_fields) + ['source_pos_order_partner_id']

    def _get_signature(self):
        return self.source_pos_order_id.user_id.signature or super()._get_signature()

    def _compute_use_count(self):
        super()._compute_use_count()
        read_group_res = self.env['pos.order.line']._read_group(
            [('coupon_id', 'in', self.ids)], ['coupon_id'], ['__count'])
        count_per_coupon = {coupon.id: count for coupon, count in read_group_res}
        for card in self:
            card.use_count += count_per_coupon.get(card.id, 0)

    @api.model
    def validate_gift_card(self, gift_code):
        gift_card = self.search([('code', '=', gift_code)], limit=1)
        if [i for i in gift_card.history_ids.mapped('order_id') if i]:
            return {
                'status': False,
                'id': gift_card.id,
            }
        else:
            return {
                'status': True,
                'id': gift_card.id,
                'code': gift_card.code,
                'points': gift_card.points,
                'expiration_date': gift_card.expiration_date,
            }
