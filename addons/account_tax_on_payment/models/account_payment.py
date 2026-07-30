# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _, Command
from odoo.exceptions import UserError, RedirectWarning


class AccountPayment(models.Model):
    _inherit = "account.payment"

    tax_ids = fields.Many2many('account.tax', string="Taxes")

    def _prepare_move_line_tax_default_vals(self):
        self.ensure_one()
        currency_id = self.currency_id.id
        lines_vals = []
        counterpart_vals = []
        liquidity_balance = self.currency_id._convert(
            self.amount,
            self.company_id.currency_id,
            self.company_id,
            self.date,
        )
        sign = -1 if self.payment_type == 'outbound' else 1
        taxes_res = self.tax_ids.with_context(force_price_include=True).compute_all(liquidity_balance, self.company_id.currency_id)
        total_tax_amount = 0.00
        for tax_res in taxes_res['taxes']:
            amount = tax_res['amount'] * sign * -1
            total_tax_amount += tax_res['amount']
            lines_vals.append({
                'name': tax_res['name'],
                'account_id': tax_res['account_id'],
                'partner_id': self.partner_id.id,
                'debit': amount if amount > 0.0 else 0.0,
                'credit': -amount if amount < 0.0 else 0.0,
                'tax_tag_ids': tax_res['tag_ids'],
                'display_type': 'advance_tax'
            })
        if total_tax_amount:
            counterpart_account_id = self.company_id.account_advance_payment_tax_account_id.id
            if not counterpart_account_id:
                error_msg = _("To use tax on payment you need to set advance payment tax account on the configuration panel")
                if self.env.is_admin():
                    action = self.env.ref('account.action_account_config')
                    raise RedirectWarning(error_msg, action.id, _('Go to the configuration panel'))
                raise UserError(error_msg + _(", please contact administrator"))
            total_tax_amount = total_tax_amount * sign
            counterpart_vals.append({
                'name': "Tax Counter Part",
                'date_maturity': self.date,
                'currency_id': currency_id,
                'debit': total_tax_amount if total_tax_amount > 0.0 else 0.0,
                'credit': -total_tax_amount if total_tax_amount < 0.0 else 0.0,
                'partner_id': self.partner_id.id,
                'account_id': counterpart_account_id,
                'display_type': 'advance_tax'
            })
        return lines_vals, counterpart_vals

    def _prepare_move_line_default_vals(self, write_off_line_vals=None):
        res = super()._prepare_move_line_default_vals(write_off_line_vals)
        # handel by _synchronize_to_moves if this context found
        if self._context.get('skip_account_move_synchronization'):
            return res
        if self.tax_ids:
            lines_vals, counterpart_vals = self._prepare_move_line_tax_default_vals()
            return res + lines_vals + counterpart_vals
        return res

    def _synchronize_to_moves(self, changed_fields):
        ''' Update the account.move regarding the modified account.payment.
        :param changed_fields: A list containing all modified fields on account.payment.
        '''
        super()._synchronize_to_moves(changed_fields)
        if self._context.get('skip_account_move_synchronization'):
            return

        if not any(field_name in changed_fields for field_name in self._get_trigger_fields_to_synchronize() + ('tax_ids',)):
            return

        for pay in self.with_context(skip_account_move_synchronization=True):
            line_ids_commands = []
            tax_lines_vals, counterpart_vals = pay._prepare_move_line_tax_default_vals()
            tax_counterpart_line = pay.move_id.line_ids.filtered(lambda l: l.account_id == self.company_id.account_advance_payment_tax_account_id)
            tax_lines = pay.move_id.line_ids.filtered(lambda l: l.display_type == 'advance_tax') - tax_counterpart_line
            if counterpart_vals:
                line_ids_commands.append(Command.update(tax_counterpart_line.id, counterpart_vals[0]) if tax_counterpart_line else Command.create(counterpart_vals[0]))
            elif tax_counterpart_line:
                line_ids_commands.append(Command.delete(tax_counterpart_line.id))
            for index, tax_line in enumerate(tax_lines):
                if len(tax_lines_vals) > index:
                    line_ids_commands.append(Command.update(tax_line.id, tax_lines_vals.pop(index)))
                else:
                    line_ids_commands.append(Command.delete(tax_line.id))
            for tax_line_vals in tax_lines_vals:
                line_ids_commands.append(Command.create(tax_line_vals))
            if line_ids_commands:
                pay.move_id.write({
                    'line_ids': line_ids_commands,
                })

    def _synchronize_from_moves(self, changed_fields):
        if self._context.get('skip_account_move_synchronization') or 'is_payment' in self._context:
            return
        if 'line_ids' in changed_fields:
            for pay in self:
                if pay.tax_ids:
                    raise UserError(_("You can't edit lines when tax is selected on the payment"))
        return super()._synchronize_from_moves(changed_fields)

    def _seek_for_lines(self):
        liquidity_lines, counterpart_lines, writeoff_lines = super()._seek_for_lines()
        if self.tax_ids:
            writeoff_lines = writeoff_lines.filtered(lambda l: not l.display_type == 'advance_tax')
            liquidity_lines = liquidity_lines.filtered(lambda l: not l.display_type == 'advance_tax')
            counterpart_lines = counterpart_lines.filtered(lambda l: not l.display_type == 'advance_tax')
        return liquidity_lines, counterpart_lines, writeoff_lines
