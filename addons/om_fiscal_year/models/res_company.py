# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import RedirectWarning, ValidationError


class ResCompany(models.Model):
    _inherit = 'res.company'

    # RedirectWarning is changed with validation error to remove error of missing reconciliation view
    def _validate_fiscalyear_lock(self, values):
        if values.get('fiscalyear_lock_date'):
            draft_entries = self.env['account.move'].search([
                ('company_id', 'in', self.ids),
                ('state', '=', 'draft'),
                ('date', '<=', values['fiscalyear_lock_date'])])
            if draft_entries:
                error_msg = _(
                    'There are still unposted entries in the period you want to lock. You should either post or delete them.')
                action_error = {
                    'view_mode': 'tree',
                    'name': 'Unposted Entries',
                    'res_model': 'account.move',
                    'type': 'ir.actions.act_window',
                    'domain': [('id', 'in', draft_entries.ids)],
                    'search_view_id': [self.env.ref('account.view_account_move_filter').id, 'search'],
                    'views': [[self.env.ref('account.view_move_tree').id, 'list'],
                              [self.env.ref('account.view_move_form').id, 'form']],
                }
                raise RedirectWarning(error_msg, action_error, _('Show unposted entries'))

            unreconciled_statement_lines = self.env['account.bank.statement.line'].search([
                ('company_id', 'in', self.ids),
                ('is_reconciled', '=', False),
                ('date', '<=', values['fiscalyear_lock_date']),
                ('move_id.state', 'in', ('draft', 'posted')),
            ])
            if unreconciled_statement_lines:
                error_msg = _("There are still unreconciled bank statement lines in the period you want to lock."
                              "You should either reconcile or delete them.")
                raise ValidationError(error_msg)
