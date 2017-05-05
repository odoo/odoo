# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountAccount(models.Model):
    _inherit = 'account.account'

    opening_debit = fields.Monetary(string="Opening debit", compute='_compute_opening_debit_credit', inverse='_set_opening_debit', help="Opening debit value for this account.")
    opening_credit = fields.Monetary(string="Opening credit", compute='_compute_opening_debit_credit', inverse='_set_opening_credit', help="Opening credit value for this account.")

    def _compute_opening_debit_credit(self):
        for record in self:
            opening_move = record.company_id.account_accountant_opening_move_id
            opening_move_lines = record.env['account.move.line'].search([('account_id','=',record.id), ('move_id','=',opening_move and opening_move.id or False)])
            record.opening_debit = 0.0
            record.opening_credit = 0.0
            for line in opening_move_lines: #should execute at most twice: once for credit, once for debit
                if line.debit:
                    record.opening_debit = line.debit
                elif line.credit:
                    record.opening_credit = line.credit

    def _set_opening_debit(self):
        self._set_opening_debit_credit(self.opening_debit, 'debit')

    def _set_opening_credit(self):
        self._set_opening_debit_credit(self.opening_credit, 'credit')

    def _set_opening_debit_credit(self, amount, field):
        """ Generic function called by both opening_debit and opening_credit's
        inverse function. 'Amount' parameter is the value to be set, and field
        either 'debit' or 'credit', depending on wich one of these two fields
        got assigned.
        """
        opening_move = self.company_id.account_accountant_opening_move_id

        if not opening_move:
            raise UserError("No opening move defined !")

        if opening_move.state == 'draft':
            # We first check whether we should create a new move line of modify an existing one
            opening_move_line = self.env['account.move.line'].search([('account_id','=',self.id), ('move_id','=',opening_move and opening_move.id or False), (field,'!=',0.0)])

            if opening_move_line:
                if amount:
                    # Then, we modify the line
                    setattr(opening_move_line.with_context({'check_move_validity': False}), field, amount)
                else:
                    # Then, we delete the line (no need to keep a line with value = 0)
                    opening_move_line.with_context({'check_move_validity': False}).unlink()
            elif amount:
                # Then, we create a new line, as none existed before
                self.env['account.move.line'].with_context({'check_move_validity': False}).create({
                        'name': _('Opening writing'),
                        field: amount,
                        'move_id': opening_move.id,
                        'account_id': self.id,
                })
            # Else, if opening_debit is zero, then nothing is to be done