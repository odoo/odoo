# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import api, fields, models


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
    program_type = fields.Selection(related='card_id.program_type')
    company_id = fields.Many2one(related='card_id.company_id')

    description = fields.Text(required=True)

    available_issued_points = fields.Float('Available', readonly=True)
    issued = fields.Float(readonly=True)
    used = fields.Float(
        readonly=True,
        help="Indicates the number of points claimed on a sale order;"
             " not necessarily deducted from the points issued on the same line.",
    )
    active = fields.Boolean(default=True)
    expiration_date = fields.Date('Expiration')

    order_model = fields.Char(readonly=True)
    order_id = fields.Many2oneReference(model_field='order_model', readonly=True)

    def _get_order_portal_url(self):
        self.ensure_one()
        return False

    def _get_order_description(self):
        self.ensure_one()
        return self.env[self.order_model].browse(self.order_id).display_name

    @api.model_create_multi
    def create(self, vals_list):
        today = fields.Date.today()
        for vals in vals_list:
            if vals.get('available_issued_points') == 0:
                vals['active'] = False
                continue
            card = self.env['loyalty.card'].browse(vals.get('card_id'))
            if expire_after := card.program_id.expire_after:
                vals['expiration_date'] = today + timedelta(days=expire_after)

        return super().create(vals_list)

    def write(self, vals):
        result = super().write(vals)
        today = fields.Date.today()
        if 'expiration_date' in vals:
            for line in self:
                if line.expiration_date < today:
                    line.card_id.points -= line.available_issued_points
                    line.available_issued_points = 0
                    line.active = False
        return result

    def redeem_loyalty_points(self, redemption_records):
        """
        Redeems loyalty points by prioritizing those closest to expiration.

        Points are consumed in the following order:
        1. Points with the nearest upcoming expiration date (soonest first).
        2. If expiration dates are the same, older earned points are used first.
        3. Points without any expiration date are used last.
        """
        def _redeem_from_history_lines(card_id, points_to_redeem):
            redeemable_history_lines = self.search([
                ('card_id', '=', card_id),
                ('available_issued_points', '>', 0),
            ])
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
                points_to_redeem -= redeemable_points
                if history_line.available_issued_points == 0:
                    history_line.active = False
                if points_to_redeem == 0:
                    break

        if isinstance(redemption_records, list):
            for coupon in redemption_records:
                card_id = coupon.get('card_id')
                points_to_redeem = coupon.get('points_to_redeem')
                _redeem_from_history_lines(card_id, points_to_redeem)

        elif isinstance(redemption_records, (float, int)):
            _redeem_from_history_lines(self.card_id.id, redemption_records)

    @api.model
    def _cron_expire_loyalty_points(self):
        """
        Expire and archive history lines and recompute total card balance.
        """
        today = fields.Date.today()
        expired_lines = self.search([('expiration_date', '<', today)])

        if not expired_lines:
            return

        for line in expired_lines:
            line.card_id.points -= line.available_issued_points

        expired_lines.write({
            'available_issued_points': 0,
            'active': False,
        })
