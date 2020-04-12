# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.misc import format_date, formatLang

from collections import defaultdict

import json


class AccountTransferWizard(models.TransientModel):
    _name = 'account.transfer.wizard'
    _description = "Account Transfer Wizard"

    move_line_ids = fields.One2many(string="Journal Items", comodel_name='account.move.line', compute="_retrieve_fields_from_context", help="Journal entries to transfer accounts from.")
    destination_account_id = fields.Many2one(string="To", comodel_name='account.account', help="Account to transfer to.")
    journal_id = fields.Many2one(string="Journal", comodel_name='account.journal', help="Journal where to create the transfer entry.")
    date = fields.Date(string="Date", help="Date to be set on the transfer entry.", default=fields.Date.today)
    company_id = fields.Many2one(string="Company", comodel_name='res.company', compute='_retrieve_fields_from_context')
    display_currency_helper = fields.Boolean(string="Currency Conversion Helper", compute='_compute_display_currency_helper', help="Technical field used to indicate whether or not to display the tooltip informing a currency conversion will be performed with the transfer")
    aml_preview_data = fields.Text(string="AML Preview Data", compute='_compute_aml_preview_data', help="Preview JSON data for aml preview widget")

    @api.depends_context('active_model')
    def _retrieve_fields_from_context(self):
        if self._context.get('active_model') == 'account.move.line':
            aml = self.env['account.move.line'].browse(self._context.get('active_ids', []))

            company = aml.mapped('company_id')
            if len(company) > 1:
                raise UserError(_("You cannot create a transfer for entries belonging to different companies."))

            for record in self:
                record.move_line_ids = aml
                record.company_id = company
        else:
            raise UserError(_("Transfer wizard should only be called on account.move.line objects"))

    @api.depends('destination_account_id')
    def _compute_display_currency_helper(self):
        for record in self:
            record.display_currency_helper = bool(record.destination_account_id.currency_id)

    @api.depends('destination_account_id')
    def _compute_aml_preview_data(self):
        for record in self:
            record.aml_preview_data = json.dumps({
                'groups_vals': [self.env['account.move']._move_dict_to_preview_vals(self._get_move_to_create_dict(), record.company_id.currency_id)],
                'options': {
                    'columns': [
                        {'field': 'account_id', 'label': _('Account')},
                        {'field': 'name', 'label': _('Label')},
                        {'field': 'partner_id', 'label': _('Partner')},
                        {'field': 'debit', 'label': _('Debit'), 'class': 'text-right text-nowrap'},
                        {'field': 'credit', 'label': _('Credit'), 'class': 'text-right text-nowrap'},
                    ],
                },
            })

    def _get_move_to_create_dict(self):
        line_vals = []

        # Group data from selected move lines
        counterpart_balances = defaultdict(lambda: defaultdict(lambda: 0))
        grouped_source_lines =  defaultdict(lambda: self.env['account.move.line'])

        for line in self.move_line_ids.filtered(lambda x: x.account_id != self.destination_account_id):
            counterpart_currency = line.currency_id
            counterpart_amount_currency = line.amount_currency

            if self.destination_account_id.currency_id and self.destination_account_id.currency_id != self.company_id.currency_id:
                counterpart_currency = self.destination_account_id.currency_id
                counterpart_amount_currency = self.company_id.currency_id._convert(line.balance, self.destination_account_id.currency_id, self.company_id, line.date)

            if counterpart_currency:
                counterpart_balances[(line.partner_id, counterpart_currency)]['amount_currency'] += counterpart_amount_currency

            counterpart_balances[(line.partner_id, counterpart_currency)]['balance'] += line.balance
            grouped_source_lines[(line.partner_id, line.currency_id, line.account_id)] += line

        # Generate counterpart lines' vals
        for (counterpart_partner, counterpart_currency), counterpart_vals in counterpart_balances.items():
            source_accounts = self.move_line_ids.mapped('account_id')
            counterpart_label = len(source_accounts) == 1 and _("Transfer from %s") % source_accounts.display_name or _("Transfer counterpart")

            if not self.company_id.currency_id.is_zero(counterpart_vals['balance']) or (counterpart_currency and not counterpart_currency.is_zero(counterpart_vals['amount_currency'])):
                line_vals.append({
                    'name': counterpart_label,
                    'debit': counterpart_vals['balance'] > 0 and self.company_id.currency_id.round(counterpart_vals['balance']) or 0,
                    'credit': counterpart_vals['balance'] < 0 and self.company_id.currency_id.round(-counterpart_vals['balance']) or 0,
                    'account_id': self.destination_account_id.id,
                    'partner_id': counterpart_partner.id or None,
                    'amount_currency': counterpart_currency and counterpart_currency.round((counterpart_vals['balance'] < 0 and -1 or 1) * abs(counterpart_vals['amount_currency'])) or 0,
                    'currency_id': counterpart_currency.id or None,
                })

        # Generate transfer lines' vals
        for (partner, currency, account), lines in grouped_source_lines.items():
            account_balance = sum(line.balance for line in lines)
            if not (currency or self.company_id.currency_id).is_zero(account_balance):
                account_amount_currency = currency and currency.round(sum(line.amount_currency for line in lines)) or 0
                line_vals.append({
                    'name': _('Transfer to %s') % (self.destination_account_id.display_name or _('Destination Account')),
                    'debit': account_balance < 0 and self.company_id.currency_id.round(-account_balance) or 0,
                    'credit': account_balance > 0 and self.company_id.currency_id.round(account_balance) or 0,
                    'account_id': account.id,
                    'partner_id': partner.id or None,
                    'currency_id': currency.id or None,
                    'amount_currency': (account_balance > 0 and -1 or 1) * abs(account_amount_currency),
                })

        return {
            'journal_id': self.journal_id.id,
            'date': self.date,
            'ref': self.destination_account_id.display_name and _("Transfer entry to %s") % self.destination_account_id.display_name or '',
            'line_ids': [(0, 0, line) for line in line_vals],
        }

    def button_transfer(self):
        new_move = self.env['account.move'].create(self._get_move_to_create_dict())
        new_move.post()

        # Group lines
        grouped_lines = defaultdict(lambda: self.env['account.move.line'])
        destination_lines = self.move_line_ids.filtered(lambda x: x.account_id == self.destination_account_id)
        for line in self.move_line_ids - destination_lines:
            grouped_lines[(line.partner_id, line.currency_id, line.account_id)] += line

        # Reconcile
        for (partner, currency, account), lines in grouped_lines.items():
            if account.reconcile:
                to_reconcile = lines + new_move.line_ids.filtered(lambda x: x.account_id == account and x.partner_id == partner and x.currency_id == currency)
                to_reconcile.reconcile()

            if destination_lines and self.destination_account_id.reconcile:
                to_reconcile = destination_lines + new_move.line_ids.filtered(lambda x: x.account_id == self.destination_account_id and x.partner_id == partner and x.currency_id == currency)
                to_reconcile.reconcile()

        # Log the operation on source moves
        acc_transfer_per_move = defaultdict(lambda: defaultdict(lambda: 0)) # dict(move, dict(account, balance))
        for line in self.move_line_ids:
            acc_transfer_per_move[line.move_id][line.account_id] += line.balance

        for move, balances_per_account in acc_transfer_per_move.items():
            message_to_log = self._format_source_log(balances_per_account, new_move)
            if message_to_log:
                move.message_post(body=message_to_log)

        # Log on target move as well
        new_move.message_post(body=self._format_new_move_log(acc_transfer_per_move))

        return {
            'name': _("Transfer"),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': new_move.id,
            }

    def _format_new_move_log(self, acc_transfer_per_move):
        format = _("%(amount)s %(currency_symbol)s (%(debit_credit)s) from %(link)s, <strong>%(account_source_name)s</strong>")
        rslt = _("This entry transfers the following amounts to <strong>%(destination)s</strong> <ul>") % {'destination': self.destination_account_id.display_name}
        for move, balances_per_account in acc_transfer_per_move.items():
            for account, balance in balances_per_account.items():
                if account != self.destination_account_id: # Otherwise, logging it here is confusing for the user
                    rslt += ('<li>' + format +'</li>') % {
                        'amount': abs(balance),
                        'debit_credit': balance < 0 and _('C') or _('D'),
                        'currency_symbol': self.company_id.currency_id.symbol,
                        'account_source_name': account.display_name,
                        'link': self._format_move_link(move),
                    }

        rslt += '</ul>'
        return rslt

    def _format_source_log(self, balances_per_account, transfer_move):
        transfer_format = _("%(amount)s %(currency_symbol)s (%(debit_credit)s) from <strong>%(account_source_name)s</strong> were transferred to <strong>%(account_target_name)s</strong> by %(link)s")
        content = ''
        for account, balance in balances_per_account.items():
            if account != self.destination_account_id:
                content += ('<li>' + transfer_format + '</li>') % {
                    'amount': abs(balance),
                    'debit_credit': balance < 0 and _('C') or _('D'),
                    'currency_symbol': self.company_id.currency_id.symbol,
                    'account_source_name': account.display_name,
                    'account_target_name': self.destination_account_id.display_name,
                    'link': self._format_move_link(transfer_move),
                }
        return content and '<ul>' + content + '</ul>' or None

    def _format_move_link(self, move):
        move_link_format = "<a href=# data-oe-model=account.move data-oe-id=%(move_id)s>%(move_name)s</a>"
        return move_link_format % {'move_id': move.id, 'move_name': move.name}
