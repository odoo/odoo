# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import timedelta

from odoo import api, fields, models
from odoo.tools import float_round


class LoyaltyHistory(models.Model):
    _name = 'loyalty.history'
    _description = "History for Loyalty cards and Ewallets"
    _order = 'id desc'

    card_id = fields.Many2one(
        comodel_name='loyalty.card',
        required=True,
        index=True,
        ondelete='cascade',
        readonly=True,
    )
    company_id = fields.Many2one(related='card_id.company_id')

    description = fields.Text(required=True)

    available_issued_points = fields.Float()
    issued = fields.Float(readonly=True)
    used = fields.Float(readonly=True)

    order_model = fields.Char(readonly=True)
    order_id = fields.Many2oneReference(model_field='order_model', readonly=True)
    is_line_expired = fields.Selection(
        selection=[
            ('valid', "Valid"),
            ('used', "Used"),
            ('expired', "Expired"),
        ],
        compute='_compute_is_line_expired',
    )
    expiration_date = fields.Date()

    def _compute_is_line_expired(self):
        today = fields.Date.today()
        for history_line in self:
            if history_line.expiration_date and history_line.expiration_date <= today:
                history_line.available_issued_points = 0
                history_line.is_line_expired = 'expired'
            elif not history_line.available_issued_points:
                history_line.is_line_expired = 'used'
            else:
                history_line.is_line_expired = 'valid'

    def _get_order_portal_url(self):
        self.ensure_one()
        return False

    def _get_order_description(self):
        self.ensure_one()
        return self.env[self.order_model].browse(self.order_id).display_name

    @api.model_create_multi
    def create(self, vals_list):
        now = fields.Datetime.now()
        for vals in vals_list:
            if 'expiration_date' not in vals:
                card_id = vals.get('card_id')
                card = self.env['loyalty.card'].browse(card_id)
                expire_after = card.program_id.expire_after
                if expire_after:
                    vals['expiration_date'] = now + timedelta(days=expire_after)

        return super().create(vals_list)

    def redeem_loyalty_points(self, used_points):
        """
        Redeems loyalty points by prioritizing those closest to expiration.

        Points are consumed in the following order:
        1. Points with the nearest upcoming expiration date (soonest first).
        2. If expiration dates are the same, older earned points are used first.
        3. Points without any expiration date are used last.
        """
        def _redeem_from_history_lines(history_lines, points_to_redeem):
            redeemable_history_lines = history_lines.filtered(
                lambda history_line: history_line.is_line_expired == 'valid'
                and history_line.available_issued_points > 0,
            )
            sorted_history_lines = redeemable_history_lines.sorted(
                key=lambda history_line: (
                    history_line.expiration_date is False,
                    history_line.expiration_date,
                    history_line.id,
                ),
            )

            for history_line in sorted_history_lines:
                redeemable_points = min(history_line.available_issued_points, points_to_redeem)
                history_line.available_issued_points -= redeemable_points
                if not history_line.available_issued_points:
                    history_line.is_line_expired = 'used'
                points_to_redeem -= redeemable_points

        def _redeem_points_by_card_id(self, card_id, points):
            if not card_id or points <= 0:
                return

            history_lines = self.search([('card_id', '=', card_id)])
            if history_lines:
                _redeem_from_history_lines(history_lines, points)

        if isinstance(used_points, list):
            for coupon in used_points:
                card_id = coupon.get('card_id')
                points_to_redeem = coupon.get('points_to_redeem', 0.0)

                _redeem_points_by_card_id(self, card_id, points_to_redeem)

        elif isinstance(used_points, (float, int)):
            _redeem_points_by_card_id(self, self.card_id.id, used_points)
