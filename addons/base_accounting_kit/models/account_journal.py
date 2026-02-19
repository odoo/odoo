# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2022-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################

from odoo import models, _


class AccountJournal(models.Model):
    _inherit = "account.journal"

    # def action_open_reconcile(self):
    #     self.ensure_one()
    #
    #     if self.type in ('bank', 'cash'):
    #         return self.env['account.bank.statement.line']._action_open_bank_reconciliation_widget(
    #             default_context={
    #                 'default_journal_id': self.id,
    #                 'search_default_journal_id': self.id,
    #                 'search_default_not_matched': True,
    #             },
    #         )
    #     else:
    #         # Open reconciliation view for customers/suppliers
    #         action_context = {'show_mode_selector': False, 'company_ids': self.mapped('company_id').ids}
    #         if self.type == 'sale':
    #             action_context.update({'mode': 'customers'})
    #         elif self.type == 'purchase':
    #             action_context.update({'mode': 'suppliers'})
    #         return {
    #             'type': 'ir.actions.client',
    #             'tag': 'manual_reconciliation_view',
    #             'context': action_context,
    #         }
    def action_open_reconcile(self):
        if self.type in ['bank', 'cash']:
            # Open reconciliation view for bank statements belonging to this journal
            bank_stmt = self.env['account.bank.statement'].search(
                [('journal_id', 'in', self.ids)]).mapped('line_ids')
            return {
                'type': 'ir.actions.client',
                'tag': 'bank_statement_reconciliation_view',
                'context': {'statement_line_ids': bank_stmt.ids,
                            'company_ids': self.mapped('company_id').ids},
            }
        else:
            # Open reconciliation view for customers/suppliers
            action_context = {'show_mode_selector': False,
                              'company_ids': self.mapped('company_id').ids}
            if self.type == 'sale':
                action_context.update({'mode': 'customers'})
            elif self.type == 'purchase':
                action_context.update({'mode': 'suppliers'})
            return {
                'type': 'ir.actions.client',
                'tag': 'manual_reconciliation_view',
                'context': action_context,
            }

    def create_cash_statement(self):
        """for redirecting in to bank statement lines"""
        return {
            'name': _("Statements"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.bank.statement.line',
            'view_mode': 'list,form',
            'context': {'default_journal_id': self.id},
        }
