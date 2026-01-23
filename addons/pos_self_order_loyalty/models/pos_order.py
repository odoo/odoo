# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models
from odoo.exceptions import UserError


class PosOrder(models.Model):
    _name = 'pos.order'
    _inherit = 'pos.order'

    def action_pos_order_paid(self):
        res = super().action_pos_order_paid()
        if self.source not in ['mobile', 'kiosk']:
            return res

        # Here we want to update the loyalty cards (update points, link them to order, etc.)
        # All of this only if the order is paid
        if self.state in ['draft', 'cancel']:
            return res

        card_changes = self._compute_points_change()
        lh_values = []
        for card_id, changes in card_changes.items():
            card = self.env['loyalty.card'].browse(card_id).exists()
            points = changes['points']
            used = changes['used']
            if not card or card.points + points < 0:
                raise UserError(_("Loyalty card %s does not have enough points to redeem this reward.", card.display_name))
            card.points += points
            if used:
                card.source_pos_order_id = self

            # Adding loyalty history lines
            lh_values.append({
                'order_id': self.id,
                'order_model': 'pos.order',
                'card_id': card.id,
                'used': min(points, 0),
                'issued': max(points, 0),
                'description': _('Points %(action)s via Self Order at %(config_name)s', action='added' if points > 0 else 'used', config_name=self.config_id.name),
            })

        self.env['loyalty.history'].sudo().create(lh_values)
        return res

    def _compute_points_change(self):
        # Get cards that can gain points
        loyalty_cards = self.config_id._get_program_ids().filtered(lambda p: p.program_type in ['loyalty', 'buy_x_get_y', 'promotion']).coupon_ids.filtered(lambda c: c._is_valid_for_order(self))

        card_changed = {}
        for card in loyalty_cards:
            rules = card.program_id.rule_ids
            point_to_add = 0
            for rule in rules:
                if rule._is_condition_satisfied(self):
                    point_to_add += rule._get_points_to_add(self)
            if point_to_add > 0:
                card_changed[card.id] = {'points': card_changed.get(card.id, {}).get('points', 0) + point_to_add, 'used': False}

        # Substract points used in rewards
        for line in self.lines:
            if line.is_reward_line and line.coupon_id.id:
                card_changed[line.coupon_id.id] = {
                    'points': card_changed.get(line.coupon_id.id, {}).get('points', 0) - line.points_cost,
                    'used': True,
                }

        return card_changed

    def _verify_coupon_validity(self):
        card_changes = self._compute_points_change()
        for card_id, changes in card_changes.items():
            card = self.env['loyalty.card'].browse(card_id).exists()
            points = changes['points']
            program = card.program_id
            if not card or card.points + points < 0 or (program.limit_usage and program.total_order_count >= program.max_usage):
                raise UserError(_("One of the loyalty cards linked to this order does not have enough points to redeem the selected rewards."))
