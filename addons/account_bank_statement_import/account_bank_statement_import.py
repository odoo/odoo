# -*- coding: utf-8 -*-

import base64

from openerp import api, fields, models, _
from openerp.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    # Ensure transactions can be imported only once (if the import format provides unique transaction ids)
    unique_import_id = fields.Char(string='Import ID', readonly=True, copy=False)

    _sql_constraints = [
        ('unique_import_id', 'unique (unique_import_id)', 'A bank account transactions can be imported only once !')
    ]


class AccountBankStatementImport(models.TransientModel):
    _name = 'account.bank.statement.import'
    _description = 'Import Bank Statement'

    data_file = fields.Binary(string='Bank Statement File', required=True, help='Get you bank statements in electronic format from your bank and select them here.')

    @api.multi
    def import_file(self):
        """ Process the file chosen in the wizard, create bank statement(s) and go to reconciliation. """
        self.ensure_one()
        #set the active_id in the context, so that any extension module could
        #reuse the fields chosen in the wizard if needed (see .QIF for example)
        data_file = self.data_file
        # Let the appropriate implementation module parse the file and return the required data
        # The active_id is passed in context in case an implementation module requires information about the wizard state (see QIF)
        currency_code, account_number, stmts_vals = self.with_context(active_id=self.ids[0])._parse_file(base64.b64decode(data_file))
        # Check raw data
        self._check_parsed_data(stmts_vals)
        # Try to find the currency and journal in odoo
        currency, journal, bank_account = self._find_additional_data(currency_code, account_number)
        # If no journal found, ask the user about creating one
        if not journal:
            # The active_id is passed in context so the wizard can call import_file again once the journal is created
            return self.with_context(active_id=self.ids[0])._journal_creation_wizard(currency, account_number, bank_account)
        # Prepare statement data to be used for bank statements creation
        stmts_vals = self._complete_stmts_vals(stmts_vals, journal, account_number)
        # Create the bank statements
        statement_ids, notifications = self._create_bank_statements(stmts_vals)
        # Finally dispatch to reconciliation interface
        action = self.env.ref('account.action_bank_reconcile_bank_statements')
        return {
            'name': action.name,
            'tag': action.tag,
            'context': {
                'statement_ids': statement_ids,
                'notifications': notifications
            },
            'type': 'ir.actions.client',
        }

    def _journal_creation_wizard(self, currency, account_number, bank_account):
        """ Calls a wizard that allows the user to accept/refuse journal creation """
        return {
            'name': _('Journal Creation'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.bank.statement.import.journal.creation',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'statement_import_transient_id': self.env.context['active_id'],
                'default_currency_id': currency and currency.id or False,
                'default_account_number': account_number,
                'bank_account_id': bank_account and bank_account.id or False,
                'default_name': _('Bank') + ' ' + account_number,
            }
        }

    def _parse_file(self, data_file):
        """ Each module adding a file support must extends this method. It processes the file if it can, returns super otherwise, resulting in a chain of responsability.
            This method parses the given file and returns the data required by the bank statement import process, as specified below.
            rtype: triplet (if a value can't be retrieved, use None)
                - currency code: string (e.g: 'EUR')
                    The ISO 4217 currency code, case insensitive
                - account number: string (e.g: 'BE1234567890')
                    The number of the bank account which the statement belongs to
                - bank statements data: list of dict containing (optional items marked by o) :
                    - 'name': string (e.g: '000000123')
                    - 'date': date (e.g: 2013-06-26)
                    -o 'balance_start': float (e.g: 8368.56)
                    -o 'balance_end_real': float (e.g: 8888.88)
                    - 'transactions': list of dict containing :
                        - 'name': string (e.g: 'KBC-INVESTERINGSKREDIET 787-5562831-01')
                        - 'date': date
                        - 'amount': float
                        - 'unique_import_id': string
                        -o 'account_number': string
                            Will be used to find/create the res.partner.bank in odoo
                        -o 'note': string
                        -o 'partner_name': string
                        -o 'ref': string
        """
        raise UserError(_('Could not make sense of the given file.\nDid you install the module to support this type of file ?'))

    def _check_parsed_data(self, stmts_vals):
        """ Basic and structural verifications """
        if len(stmts_vals) == 0:
            raise UserError(_('This file doesn\'t contain any statement.'))

        no_st_line = True
        for vals in stmts_vals:
            if vals['transactions'] and len(vals['transactions']) > 0:
                no_st_line = False
                break
        if no_st_line:
            raise UserError(_('This file doesn\'t contain any transaction.'))

    def _find_additional_data(self, currency_code, account_number):
        """ Get the res.currency ID and the res.partner.bank ID """
        company_currency = self.env.user.company_id.currency_id
        journal_obj = self.env['account.journal']
        currency = None

        if currency_code:
            currency = self.env['res.currency'].search([('name', '=ilike', currency_code)], limit=1)
            if not currency:
                raise osv.except_osv(_("No currency found matching '%s'.") % currency_code)
            if currency == company_currency:
                currency = False

        bank_account = None
        if account_number and len(account_number) > 4:
            bank_account = self.env['res.partner.bank'].search([('acc_number', '=', account_number)], limit=1)

        # Find the journal from context or bank account
        journal = journal_obj.browse(self._context.get('journal_id', []))
        if bank_account:
            if journal:
                if bank_account.journal_id and bank_account.journal_id != journal:
                    raise UserError(_('The account of this statement is linked to another journal.'))
                if not bank_account.journal_id:
                    bank_account.write({'journal_id': journal.id})
            else:
                if bank_account.journal_id:
                    journal = bank_account.journal_id

        # If importing into an existing journal
        if journal:
            # The bank account cannot belong to another journal
            if not bank_account and account_number:
                journal_account = self.env['res.partner.bank'].search([('journal_id', '=', journal.id)], limit=1)
                if journal_account:
                    raise UserError(_('You are importing a file from account %s while the account of journal %s is %s.') % (account_number, journal.name, journal_account.acc_number))

            # Its currency must be the same as the bank statement
            journal_currency = journal.currency_id
            if currency == None:
                currency = journal_currency
            if currency and currency != journal_currency:
                statement_cur_code = currency == False and company_currency.name or currency.name
                journal_cur_code = not journal_currency and company_currency.name or journal_currency.name
                raise UserError(_('The currency of the bank statement (%s) is not the same as the currency of the journal (%s) !') % (statement_cur_code, journal_cur_code))

        # If we couldn't find / can't create a journal, everything is lost
        if not journal and not account_number:
            raise UserError(_('Cannot find in which journal import this statement. Please manually select a journal.'))

        return currency, journal, bank_account

    def _create_bank_account(self, account_number):
        try:
            bank_type = self.env.ref('bank.bank_normal')
            bank_code = bank_type.code
        except ValueError:
            bank_code = 'bank'
        account_number = account_number.replace(' ', '').replace('-', '')
        return self.env['res.partner.bank'].create({
            'acc_number': account_number,
            'state': bank_code,
        })

    def _complete_stmts_vals(self, stmts_vals, journal, account_number):
        for st_vals in stmts_vals:
            st_vals['journal_id'] = journal.id

            for line_vals in st_vals['transactions']:
                unique_import_id = line_vals.get('unique_import_id')
                if unique_import_id:
                    line_vals['unique_import_id'] = (account_number and account_number + '-' or '') + unique_import_id

                if not line_vals.get('bank_account_id'):
                    # Find the partner and his bank account or create the bank account. The partner selected during the
                    # reconciliation process will be linked to the bank when the statement is closed.
                    partner_id = False
                    bank_account_id = False
                    identifying_string = line_vals.get('account_number')
                    if identifying_string:
                        partner_bank = self.env['res.partner.bank'].search([('acc_number', '=', identifying_string)], limit=1)
                        if partner_bank:
                            bank_account_id = partner_bank.id
                            partner_id = partner_bank.partner_id.id
                        else:
                            #do not pass the journal_id in _create_bank_account() because we don't want to link
                            #that bank_account to the journal (it belongs to a partner, not to the company)
                            bank_account_id = self._create_bank_account(identifying_string).id
                    line_vals['partner_id'] = partner_id
                    line_vals['bank_account_id'] = bank_account_id

        return stmts_vals

    def _create_bank_statements(self, stmts_vals):
        """ Create new bank statements from imported values, filtering out already imported transactions, and returns data used by the reconciliation widget """
        BankStatement = self.env['account.bank.statement']
        BankStatementLine = self.env['account.bank.statement.line']

        # Filter out already imported transactions and create statements
        statement_ids = []
        ignored_statement_lines_import_ids = []
        for st_vals in stmts_vals:
            filtered_st_lines = []
            for line_vals in st_vals['transactions']:
                if not 'unique_import_id' in line_vals \
                   or not line_vals['unique_import_id'] \
                   or not bool(BankStatementLine.sudo().search([('unique_import_id', '=', line_vals['unique_import_id'])], limit=1)):
                    filtered_st_lines.append(line_vals)
                else:
                    ignored_statement_lines_import_ids.append(line_vals['unique_import_id'])
            if len(filtered_st_lines) > 0:
                # Remove values that won't be used to create records
                st_vals.pop('transactions', None)
                for line_vals in filtered_st_lines:
                    line_vals.pop('account_number', None)
                # Create the satement
                st_vals['line_ids'] = [[0, False, line] for line in filtered_st_lines]
                statement_ids.append(BankStatement.create(st_vals).id)
        if len(statement_ids) == 0:
            raise UserError(_('You have already imported that file.'))

        # Prepare import feedback
        notifications = []
        num_ignored = len(ignored_statement_lines_import_ids)
        if num_ignored > 0:
            notifications += [{
                'type': 'warning',
                'message': _("%d transactions had already been imported and were ignored.") % num_ignored if num_ignored > 1 else _("1 transaction had already been imported and was ignored."),
                'details': {
                    'name': _('Already imported items'),
                    'model': 'account.bank.statement.line',
                    'ids': BankStatementLine.search([('unique_import_id', 'in', ignored_statement_lines_import_ids)]).ids
                }
            }]
        return statement_ids, notifications
