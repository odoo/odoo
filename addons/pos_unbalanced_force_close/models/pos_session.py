# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models
from odoo.tools import float_is_zero, float_round, float_compare
from odoo.exceptions import AccessError, UserError
import logging

_logger = logging.getLogger(__name__)


class PosSession(models.Model):
    _inherit = "pos.session"

    _allow_force_close = fields.Boolean(related='config_id.allow_force_close', readonly=True, store=False)
    _is_unbalanced = fields.Boolean('Unbalanced Journal Entry', readonly=True)

    # The 2 following fields are mainly for Support purpose, to keep an history of what have been done with the session.
    _force_close_unbalanced = fields.Boolean('Has been forced closed after unbalanced journal entry', readonly=True)
    _force_close_unbalanced_difference = fields.Float('Difference debit/credit', readonly=True)

    def _get_rounding_difference_vals(self, amount, amount_converted):
        partial_args = {
            'name':    'Rounding line',
            'move_id': self.move_id.id,
        }
        if amount > 0:  # loss
            partial_args['account_id'] = self.config_id.difference_credit_account.id
            return self._credit_amounts(partial_args, amount, amount_converted)
        else:  # profit
            partial_args['account_id'] = self.config_id.difference_debit_account.id
            return self._debit_amounts(partial_args, -amount, -amount_converted)

    def _get_extra_move_lines_vals(self):
        res = super(PosSession, self)._get_extra_move_lines_vals()
        if not self._allow_force_close or \
                not self._is_unbalanced or \
                not self.env.user._is_admin() or \
                not self.env.context.get('force_close_unbalanced'):
            return res
        rounding_difference = {'amount': 0.0, 'amount_converted': 0.0}
        rounding_vals = []
        rounding_difference['amount'] = sum(self.move_id.line_ids.mapped('debit')) - sum(self.move_id.line_ids.mapped('credit'))
        rounding_difference['amount_converted'] = rounding_difference['amount']
        if not float_is_zero(rounding_difference['amount_converted'], precision_rounding=self.company_id.currency_id.rounding):
            value = self._get_rounding_difference_vals(rounding_difference['amount'], rounding_difference['amount_converted'])
            self._force_close_unbalanced_difference = value['debit'] or value['credit']
            rounding_vals += [value]
            _logger.warning('Force Close Unbalanced POS Session. uid: {} - session_id:{} - difference:{}'.format(self.env.user.id, self.id, self._force_close_unbalanced_difference))
        return res + rounding_vals

    def action_pos_session_closing_control(self):
        # Only the admin can force close the session
        if self.env.context.get('force_close_unbalanced') and not self.env.user._is_admin():
            raise AccessError(_("Only administrators can force close the session."))

        super(PosSession, self.with_context(pos_session_id=self.id)).action_pos_session_closing_control()

        if self.env.context.get('force_close_unbalanced'):
            self._force_close_unbalanced = True

    def action_pos_session_unbalanced_force_close(self):
        # Wizard
        return {
            'name':      'Force close',
            'type':      'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'pos_unbalanced_force_close.wizard',
            'views':     [(False, 'form')],
            'view_id':   'pos_unbalanced_force_close.open_confirmation_wizard',
            'target':    'new',
            'context':   self.env.context,
        }
