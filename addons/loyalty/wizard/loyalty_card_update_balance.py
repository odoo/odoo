# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models
from odoo.exceptions import ValidationError


class LoyaltyCardUpdateBalance(models.TransientModel):
    _name = 'loyalty.card.update.balance'
    _description = "Update Loyalty Card Points"

    card_id = fields.Many2one(
        comodel_name='loyalty.card',
        required=True,
        readonly=True,
    )
    old_balance = fields.Float(related='card_id.points')
    new_balance = fields.Float()
    description = fields.Char(required=True)

    def action_update_card_point(self):
        if self.old_balance == self.new_balance or self.new_balance < 0:
            raise ValidationError(
                _("New Balance should be positive and different then old balance.")
            )
        difference = self.new_balance - self.old_balance
        used = 0
        issued = 0
        if difference > 0:
            issued = difference
            if self.old_balance < 0:
                used = abs(self.old_balance)
        else:
            used = abs(difference)

        loyalty_history = self.env['loyalty.history']
        loyalty_history.create({
            'card_id': self.card_id.id,
            'description': self.description or _("Gift for customer"),
            'used': used,
            'issued': issued,
            'available_issued_points': issued,
        })

        # Redemption cases:
        # - If card balance is negative then issued points are redeemed to compensate debt.
        # - If New balance is less than the old balance, redeem the diff to maintain balances.
        if used:
            loyalty_history.redeem_loyalty_points([{
                'card_id': self.card_id.id,
                'points_to_redeem': used,
            }])
        self.card_id.points = self.new_balance
