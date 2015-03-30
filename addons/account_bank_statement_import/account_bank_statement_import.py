# -*- coding: utf-8 -*-
import base64

from openerp import api, models, fields
from openerp.tools.translate import _
from openerp.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)


class account_bank_statement_line(models.Model):
    _inherit = "account.bank.statement.line"

    # Ensure transactions can be imported only once (if the import format
    # provides unique transaction ids)
    unique_import_id = fields.Char('Import ID', readonly=True, copy=False)

    _sql_constraints = [
        ('unique_import_id',
         'unique (unique_import_id)',
         'A bank account transactions can be imported only once !')
    ]


class account_bank_statement_import(models.TransientModel):
    _name = 'account.bank.statement.import'
    _description = 'Import Bank Statement'

    data_file = fields.Binary(
        'Bank Statement File', required=True,
        help='Get you bank statements in electronic format from your bank '
        'and select them here.')

    @api.multi
    def import_file(self):
        """ Process the file chosen in the wizard, create bank statement(s) and
        go to reconciliation. """
        self.ensure_one()
        data_file = base64.b64decode(self.data_file)
        statement_ids, notifications = self.with_context(
            active_id=self.id)._import_file(data_file)
        # dispatch to reconciliation interface
        action = self.env.ref(
            'account.action_bank_reconcile_bank_statements')
        return {
            'name': action.name,
            'tag': action.tag,
            'context': {
                'statement_ids': statement_ids,
                'notifications': notifications
            },
            'type': 'ir.actions.client',
        }

    @api.model
    def _import_file(self, data_file):
        """ Create bank statement(s) from file
        """
        # The appropriate implementation module returns the required data
        currency_code, account_number, stmts_vals = self._parse_file(data_file)
        # Check raw data
        self._check_parsed_data(stmts_vals)
        # Try to find the bank account and currency in odoo
        currency_id, bank_account_id = self._find_additional_data(
            currency_code, account_number)
        # Create the bank account if not already existing
        if not bank_account_id and account_number:
            journal_id = self.env.context.get('journal_id')
            company_id = self.env.user.company_id.id
            if journal_id:
                journal = self.env['account.journal'].browse(journal_id)
                company_id = journal.company_id.id
            bank_account_id = self._create_bank_account(
                account_number, company_id=company_id,
                currency_id=currency_id).id
        # Find or create the bank journal
        journal_id = self._get_journal(
            currency_id, bank_account_id, account_number)
        # Prepare statement data to be used for bank statements creation
        stmts_vals = self._complete_stmts_vals(
            stmts_vals, journal_id, account_number)
        # Create the bank statements
        return self._create_bank_statements(stmts_vals)

    @api.model
    def _parse_file(self, data_file):
        """ Each module adding a file support must extends this method. It
        rocesses the file if it can, returns super otherwise, resulting in a
        chain of responsability.
        This method parses the given file and returns the data required by
        the bank statement import process, as specified below.
            rtype: triplet (if a value can't be retrieved, use None)
                - currency code: string (e.g: 'EUR')
                    The ISO 4217 currency code, case insensitive
                - account number: string (e.g: 'BE1234567890')
                    The number of the bank account which the statement belongs
                    to
                - bank statements data: list of dict containing (optional
                                        items marked by o) :
                    - 'name': string (e.g: '000000123')
                    - 'date': date (e.g: 2013-06-26)
                    -o 'balance_start': float (e.g: 8368.56)
                    -o 'balance_end_real': float (e.g: 8888.88)
                    - 'transactions': list of dict containing :
                        - 'name': string
                            (e.g: 'KBC-INVESTERINGSKREDIET 787-5562831-01')
                        - 'date': date
                        - 'amount': float
                        - 'unique_import_id': string
                        -o 'account_number': string
                            Will be used to find/create the res.partner.bank
                            in odoo
                        -o 'note': string
                        -o 'partner_name': string
                        -o 'ref': string
        """
        raise UserError(_('Could not make sense of the given file.\nDid you '
                        'install the module to support this type of file ?'))

    @api.model
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

    @api.model
    def _find_additional_data(self, currency_code, account_number):
        """ Get the res.currency ID and the res.partner.bank ID """
        # if no currency_code is provided, we'll use the company currency
        currency_id = False
        if currency_code:
            currency_ids = self.env['res.currency'].search(
                [('name', '=ilike', currency_code)])
            company_currency_id = self.env.user.company_id.currency_id
            if currency_ids:
                if currency_ids[0] != company_currency_id:
                    currency_id = currency_ids[0].id

        bank_account_id = None
        if account_number and len(account_number) > 4:
            bank_account_ids = self.env['res.partner.bank'].search(
                [('acc_number', '=', account_number)], limit=1)
            if bank_account_ids:
                bank_account_id = bank_account_ids[0].id

        return currency_id, bank_account_id

    @api.model
    def _get_journal(self, currency_id, bank_account_id, account_number):
        """ Find or create the journal """
        bank_model = self.env['res.partner.bank']

        # Find the journal from context or bank account
        journal_id = self.env.context.get('journal_id')
        if bank_account_id:
            bank_account = bank_model.browse(bank_account_id)
            if journal_id:
                if (bank_account.journal_id.id and
                        bank_account.journal_id.id != journal_id):
                    raise UserError(
                        _('The account of this statement is linked to '
                          'another journal.'))
                if not bank_account.journal_id.id:
                    bank_model.write({'journal_id': journal_id})
            else:
                if bank_account.journal_id.id:
                    journal_id = bank_account.journal_id.id

        # If importing into an existing journal, its currency must be the same
        # as the bank statement
        if journal_id:
            journal_currency_id = self.env['account.journal'].browse(
                journal_id).currency.id
            if currency_id and currency_id != journal_currency_id:
                raise UserError(_('The currency of the bank statement is not '
                                'the same as the currency of the journal !'))

        return journal_id

    @api.model
    @api.returns('res.partner.bank')
    def _create_bank_account(self, account_number, company_id=False,
                             currency_id=False):
        try:
            bank_type = self.env.ref('base.bank_normal')
            bank_code = bank_type.code
        except ValueError:
            bank_code = 'bank'
        vals_acc = {
            'acc_number': account_number,
            'state': bank_code,
        }
        # Odoo users bank accounts (which we import statement from) have
        # company_id and journal_id set while 'counterpart' bank accounts
        # (from which statement transactions originate) don't.
        # Warning : if company_id is set, the method post_write of class
        # bank will create a journal
        if company_id:
            vals = self.env['res.partner.bank'].onchange_company_id(company_id)
            vals_acc.update(vals.get('value', {}))
            vals_acc['company_id'] = company_id

        # When the journal is created at same time of the bank account, we need
        # to specify the currency to use for the account.account and
        # account.journal
        return self.env['res.partner.bank'].with_context(
            default_currency_id=currency_id,
            default_currency=currency_id).create(vals_acc)

    @api.model
    def _complete_stmts_vals(self, stmts_vals, journal_id, account_number):
        for st_vals in stmts_vals:
            st_vals['journal_id'] = journal_id

            for line_vals in st_vals['transactions']:
                unique_import_id = line_vals.get('unique_import_id', False)
                if unique_import_id:
                    line_vals['unique_import_id'] = (
                        account_number and account_number + '-' or '') + \
                        unique_import_id

                if not line_vals.get('bank_account_id'):
                    # Find the partner and his bank account or create the bank
                    # account. The partner selected during the reconciliation
                    # process will be linked to the bank when the statement is
                    # closed.
                    partner_id = False
                    bank_account_id = False
                    identifying_string = line_vals.get('account_number')
                    if identifying_string:
                        bank_model = self.env['res.partner.bank']
                        banks = bank_model.search(
                            [('acc_number', '=', identifying_string)], limit=1)
                        if banks:
                            bank_account_id = banks[0].id
                            partner_id = banks[0].partner_id.id
                        else:
                            bank_account_id = self._create_bank_account(
                                identifying_string).id
                    line_vals['partner_id'] = partner_id
                    line_vals['bank_account_id'] = bank_account_id

        return stmts_vals

    @api.model
    def _create_bank_statements(self, stmts_vals):
        """ Create new bank statements from imported values, filtering out
        already imported transactions, and returns data used by the
        reconciliation widget
        """
        bs_model = self.env['account.bank.statement']
        bsl_model = self.env['account.bank.statement.line']

        # Filter out already imported transactions and create statements
        statement_ids = []
        ignored_statement_lines_import_ids = []
        for st_vals in stmts_vals:
            filtered_st_lines = []
            for line_vals in st_vals['transactions']:
                if 'unique_import_id' not in line_vals \
                   or not line_vals['unique_import_id'] \
                   or not bool(bsl_model.sudo().search(
                        [('unique_import_id', '=',
                          line_vals['unique_import_id'])],
                        limit=1)):
                    filtered_st_lines.append(line_vals)
                else:
                    ignored_statement_lines_import_ids.append(
                        line_vals['unique_import_id'])
            if len(filtered_st_lines) > 0:
                # Remove values that won't be used to create records
                st_vals.pop('transactions', None)
                for line_vals in filtered_st_lines:
                    line_vals.pop('account_number', None)
                # Create the satement
                st_vals['line_ids'] = [[0, False, line] for line in
                                       filtered_st_lines]
                statement_ids.append(bs_model.create(st_vals).id)
        if len(statement_ids) == 0:
            raise UserError(_('You have already imported that file.'))

        # Prepare import feedback
        notifications = []
        num_ignored = len(ignored_statement_lines_import_ids)
        if num_ignored > 0:
            notifications += [{
                'type': 'warning',
                'message': _("%d transactions had already been imported and "
                             "were ignored.") % num_ignored
                        if num_ignored > 1
                        else _("1 transaction had already been imported and "
                               "was ignored."),
                'details': {
                    'name': _('Already imported items'),
                    'model': 'account.bank.statement.line',
                    'ids': bsl_model.search(
                        [('unique_import_id', 'in',
                          ignored_statement_lines_import_ids)]).ids
                }
            }]

        return statement_ids, notifications
