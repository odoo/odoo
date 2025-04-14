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
        is_increase = difference > 0
        points_to_process = abs(difference)

        loyalty_history = self.env['loyalty.history']
        history_line = loyalty_history.create({
            'card_id': self.card_id.id,
            'description': self.description,
            'issued': points_to_process if is_increase else 0,
            'available_issued_points': points_to_process if is_increase else 0,
            'used': 0 if is_increase else points_to_process,
        })

        if is_increase:
            if self.old_balance < 0:
                history_line.compensate_existing_debts()
        else:
            loyalty_history.redeem_loyalty_points([{
                'card_id': self.card_id.id,
                'redeemer_history_line_id': history_line.id,
                'points_to_redeem': points_to_process,
            }])

        self.card_id.points = self.new_balance
