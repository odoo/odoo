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
        rec = self.with_context(active_id=self.ids[0])
        #set the active_id in the context, so that any extension module could
        #reuse the fields chosen in the wizard if needed (see .QIF for example)
        data_file = self.data_file
        # The appropriate implementation module returns the required data
        currency_code, account_number, stmts_vals = rec._parse_file(base64.b64decode(data_file))
        # Check raw data
        rec._check_parsed_data(stmts_vals)
        # Try to find the bank account and currency in odoo
        currency_id, bank_account_id = rec._find_additional_data(currency_code, account_number)
        # Find or create the bank journal
        journal_id = rec._get_journal(currency_id, bank_account_id, account_number)
        # Create the bank account if not already existing
        if not bank_account_id and account_number:
            rec._create_bank_account(account_number, journal_id=journal_id)
        # Prepare statement data to be used for bank statements creation
        stmts_vals = rec._complete_stmts_vals(stmts_vals, journal_id, account_number)
        # Create the bank statements
        statement_ids, notifications = rec._create_bank_statements(stmts_vals)
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
        currency_id = False  # So if no currency_code is provided, we'll use the company currency
        if currency_code:
            currency = self.env['res.currency'].search([('name', '=ilike', currency_code)], limit=1)
            company_currency = self.env.user.company_id.currency_id
            if currency.id != company_currency.id:
                currency_id = currency.id

        bank_account_id = None
        if account_number and len(account_number) > 4:
            account_number = account_number.replace(' ', '').replace('-', '')
            self.env.cr.execute("select id from res_partner_bank where replace(replace(acc_number,' ',''),'-','') = %s", (account_number,))
            bank_account_ids = [id[0] for id in self.env.cr.fetchall()]
            bank_account_ids = self.env['res.partner.bank'].search([('id', 'in', bank_account_ids)], limit=1)
            if bank_account_ids:
                bank_account_id = bank_account_ids.id

        return currency_id, bank_account_id

    def _get_journal(self, currency_id, bank_account_id, account_number):
        """ Find or create the journal """
        ResPartnerBank = self.env['res.partner.bank']

        # Find the journal from context or bank account
        journal_id = self._context.get('journal_id')
        if bank_account_id:
            bank_account = ResPartnerBank.browse(bank_account_id)
            if journal_id:
                if bank_account.journal_id.id and bank_account.journal_id.id != journal_id:
                    raise UserError(_('The account of this statement is linked to another journal.'))
                if not bank_account.journal_id.id:
                    bank_account.write({'journal_id': journal_id})
            else:
                if bank_account.journal_id.id:
                    journal_id = bank_account.journal_id.id

        # If importing into an existing journal, its currency must be the same as the bank statement
        if journal_id:
            journal_currency_id = self.env['account.journal'].browse(journal_id).currency_id.id
            if currency_id and currency_id != journal_currency_id:
                raise UserError(_('The currency of the bank statement is not the same as the currency of the journal !'))

        # If there is no journal, create one (and its account)
        if not journal_id and account_number:
            company = self.env.user.company_id
            journal_vals = self.env['account.journal']._prepare_bank_journal(company, {'account_type': 'bank', 'acc_name': account_number, 'currency_id': currency_id})
            journal_id = self.env['account.journal'].create(journal_vals).id
            if bank_account_id:
                bank_account.write({'journal_id': journal_id})

        # If we couldn't find/create a journal, everything is lost
        if not journal_id:
            raise UserError(_('Cannot find in which journal import this statement. Please manually select a journal.'))
        return journal_id

    def _create_bank_account(self, account_number, journal_id=False):
        try:
            bank_type = self.env.ref('bank.bank_normal')
            bank_code = bank_type.code
        except ValueError:
            bank_code = 'bank'
        account_number = account_number.replace(' ', '').replace('-', '')
        vals_acc = {
            'acc_number': account_number,
            'state': bank_code,
        }
        # Odoo users bank accounts (which we import statement from) have company_id and journal_id set
        # while 'counterpart' bank accounts (from which statement transactions originate) don't.
        if journal_id:
            vals_acc['journal_id'] = journal_id
            vals_acc['company_id'] = self.env.user.company_id.id
            vals_acc['partner_id'] = self.env.user.company_id.partner_id.id

        return self.env['res.partner.bank'].create(vals_acc)

    def _complete_stmts_vals(self, stmts_vals, journal_id, account_number):
        for st_vals in stmts_vals:
            st_vals['journal_id'] = journal_id

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
