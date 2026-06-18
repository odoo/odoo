# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    is_reward_line = fields.Boolean(
        help="Whether this line is part of a reward or not.")
    reward_id = fields.Many2one(
        'loyalty.reward', "Reward", ondelete='restrict',
        help="The reward associated with this line.", index='btree_not_null')
    card_id = fields.Many2one(
        'loyalty.card', "Card", ondelete='restrict',
        help="The card used to claim that reward.", index='btree_not_null')
    points_cost = fields.Float(help="How many points this reward cost.")
    gift_card_vals = fields.Json(
        copy=False,
        help="POS-only: the gift-card/eWallet program (and optional physical code and "
             "expiration date) this funding line sold. The loyalty.card is created from it "
             "when the order is saved; afterwards card_id holds the durable link.")

    @api.model
    def _load_pos_data_fields(self, config):
        params = super()._load_pos_data_fields(config)
        params += ['is_reward_line', 'reward_id', 'points_cost', 'card_id', 'gift_card_vals']
        return params

    def _get_loyalty_program(self):
        """
        The loyalty program this line targets: its resolved card's program, or the
        pending program recorded in `gift_card_vals` before the card is created.
        mirror of *static/src/app/models/pos_order_line.js* PosOrderline.payment_program_id
        """
        self.ensure_one()
        if self.card_id:
            return self.card_id.program_id
        program_id = (self.gift_card_vals or {}).get('program_id')
        return self.env['loyalty.program'].browse(program_id) if program_id else self.env['loyalty.program']

    def _has_discount(self):
        return super()._has_discount() or (self.is_reward_line and self.reward_id.reward_type == 'discount')

    def _get_discount_amount_for_report(self):
        if self.is_reward_line:
            return abs(self.price_subtotal_incl)
        return super()._get_discount_amount_for_report()
