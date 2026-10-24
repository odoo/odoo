# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime

from odoo import Command, _, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _pre_action_done_hook(self):
        res = super()._pre_action_done_hook()
        # We use the 'skip_expired' context key to avoid to make the check when
        # user did already confirmed the wizard about expired lots.
        if res is True and not self.env.context.get('skip_expired'):
            if action := self._action_generate_expired_wizard():
                return action
        return res

    def _action_generate_expired_wizard(self):
        move_lines_with_removal_warning = self._get_move_lines_with_removal_warning()
        if not (move_lines_with_removal_warning):
            return None
        view_id = self.env.ref('product_expiry.confirm_expiry_view').id
        context = dict(self.env.context)

        context.update({
            'default_move_line_ids': [Command.set(move_lines_with_removal_warning.ids)],
        })
        return {
            'name': _('Confirmation'),
            'type': 'ir.actions.act_window',
            'res_model': 'expiry.picking.confirmation',
            'view_mode': 'form',
            'views': [(view_id, 'form')],
            'view_id': view_id,
            'target': 'new',
            'context': context,
        }

    def action_detailed_operations(self):
        action = super().action_detailed_operations()
        if any(self.move_ids.mapped('use_expiration_date')):
            action['context'].update({
                'show_lot_removal_date': True,
                'show_lot_expiration_date': self.use_create_lots,
            })
        return action

    def _get_move_lines_with_removal_warning(self):
        current_datetime = datetime.now()
        return self.move_line_ids.filtered(
            lambda ml: ml.use_expiration_date and (ml.lot_id.product_expiry_alert or (
                (removal_date := ml._get_removal_date()) and removal_date <= current_datetime
            ))
        )
