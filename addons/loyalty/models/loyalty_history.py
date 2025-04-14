# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class LoyaltyHistory(models.Model):
    _name = 'loyalty.history'
    _description = "History for Loyalty cards and Ewallets"
    _order = 'id desc'

    active = fields.Boolean(default=True)
    card_id = fields.Many2one(
        comodel_name='loyalty.card',
        ondelete='cascade',
        readonly=True,
        required=True,
        index=True,
    )
    program_type = fields.Selection(related='card_id.program_type')
    company_id = fields.Many2one(related='card_id.company_id')

    description = fields.Text(required=True)

    issued = fields.Float(readonly=True)
    available_issued_points = fields.Float(string='Available', readonly=True)
    used = fields.Float(
        help="Indicates the number of points claimed on a sale order;"
             " not necessarily deducted from the points issued on the same line.",
        readonly=True,
    )
    expiration_date = fields.Date(string='Expiration')

    order_model = fields.Char(readonly=True)
    order_id = fields.Many2oneReference(model_field='order_model', readonly=True)

    @api.constrains('expiration_date')
    def _check_line_expiration_date(self):
        for history_line in self:
            if (
                history_line.expiration_date
                and history_line.expiration_date < fields.Date.context_today(history_line)
            ):
                raise ValidationError(self.env._(
                    "The expiry date cannot be in the past. Please select a valid date."
                ))

    def _get_sorted_history_lines(self, lines):
        """
        Sorts loyalty history lines by redemption priority.

        Points are ordered by:
            1. Nearest expiration date (soonest first).
            2. Earlier creation order, if expiration dates are equal.
            3. Points without an expiration date are placed last.
        """
        return lines.sorted(
            key=lambda line: (
                line.expiration_date is False,
                line.expiration_date,
                line.id,
            ),
        )

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
            # The history line is archived immediately as it has no redeemable points.
            if vals.get('available_issued_points') == 0:
                vals['active'] = False
                continue
            card = self.env['loyalty.card'].browse(vals.get('card_id'))
            if expire_after := card.program_id.expire_after:
                vals['expiration_date'] = today + timedelta(days=expire_after)
        return super().create(vals_list)

    def compensate_existing_debts(self):
        """
        Settle outstanding debt records when new points are issued to a card.
        """
        history_lines_mapping = self.env['loyalty.point.track'].sudo()

        for issuer_line in self:
            # Debt history lines that have negative points which needs to be compensated.
            debts = history_lines_mapping.search([
                ('issuer_line_id', '=', False),
                ('points', '<', 0),
                ('redeemer_line_id.card_id', '=', issuer_line.card_id.id),
            ])

            for debt in debts:
                debt_points = abs(debt.points)
                points_to_compensate = min(debt_points, issuer_line.available_issued_points)

                history_lines_mapping.create({
                    'issuer_line_id': issuer_line.id,
                    'redeemer_line_id': debt.redeemer_line_id.id,
                    'points': points_to_compensate,
                })

                debt.points += points_to_compensate
                if debt.points == 0:
                    debt.unlink()

                issuer_line.available_issued_points -= points_to_compensate
                if issuer_line.available_issued_points == 0:
                    issuer_line.active = False
                    break

    def redeem_loyalty_points(self, reward_values):
        """
        Allocate available issued loyalty points to cover point redemption.
        If available points are insufficient, a debt record is created with no issuer line linked.

        :param list(dict) reward_values: Redemption instructions in the following format:
            {
                'card_id': int,
                'points_to_redeem': float,
                'redeemer_history_line_id': int,
                'exclude_issuer_ids': list(int),  # optional
            }
        """
        history_lines_mapping = self.env['loyalty.point.track'].sudo()

        for reward_data in reward_values:
            card_id = reward_data.get('card_id')
            points_to_redeem = reward_data.get('points_to_redeem')
            redeemer_line_id = reward_data.get('redeemer_history_line_id')
            exclude_issuer_ids = reward_data.get('exclude_issuer_ids', [])

            # find redeemable issuer lines and sort them to use them in order
            redeemable_lines = self.search([
                ('card_id', '=', card_id),
                ('id', 'not in', exclude_issuer_ids),
            ])

            mapping_vals_list = []
            for issuer_line in self._get_sorted_history_lines(redeemable_lines):
                redeemable_points = min(issuer_line.available_issued_points, points_to_redeem)

                # Create mapping of issuer -> redeemer for tracking allocation
                mapping_vals_list.append({
                    'issuer_line_id': issuer_line.id,
                    'redeemer_line_id': redeemer_line_id,
                    'points': redeemable_points,
                })

                issuer_line.available_issued_points -= redeemable_points
                if issuer_line.available_issued_points == 0:
                    issuer_line.active = False

                points_to_redeem -= redeemable_points
                if not points_to_redeem:
                    break

            # If not fully covered, create debt mapping only for an active redeemer
            if points_to_redeem > 0:
                mapping_vals_list.append({
                    'issuer_line_id': False,
                    'redeemer_line_id': redeemer_line_id,
                    'points': -points_to_redeem,
                })

            if mapping_vals_list:
                history_lines_mapping.create(mapping_vals_list)

    @api.model
    def _cron_expire_loyalty_points(self):
        """
        Scheduled job to expire loyalty points based on expiration_date and recompute card balance.
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
