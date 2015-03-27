# -*- coding: utf-8 -*-

import base64

from openerp import SUPERUSER_ID
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)


class account_bank_statement_line(osv.osv):
    _inherit = "account.bank.statement.line"

    _columns = {
        # Ensure transactions can be imported only once (if the import format provides unique transaction ids)
        'unique_import_id': fields.char('Import ID', readonly=True, copy=False),
    }

    _sql_constraints = [
        ('unique_import_id', 'unique (unique_import_id)', 'A bank account transactions can be imported only once !')
    ]


class account_bank_statement_import(osv.TransientModel):
    _name = 'account.bank.statement.import'
    _description = 'Import Bank Statement'
    _columns = {
        'data_file': fields.binary('Bank Statement File', required=True, help='Get you bank statements in electronic format from your bank and select them here.'),
    }

    def import_file(self, cr, uid, ids, context=None):
        """ Process the file chosen in the wizard, create bank statement(s) and go to reconciliation. """
        if context is None:
            context = {}
        #set the active_id in the context, so that any extension module could
        #reuse the fields chosen in the wizard if needed (see .QIF for example)
        ctx = dict(context)
        ctx['active_id'] = ids[0]

        data_file = self.browse(cr, uid, ids[0], context=ctx).data_file

        # The appropriate implementation module returns the required data
        currency_code, account_number, stmts_vals = self._parse_file(cr, uid, base64.b64decode(data_file), context=ctx)
        # Check raw data
        self._check_parsed_data(cr, uid, stmts_vals, context=ctx)
        # Try to find the bank account and currency in odoo
        currency_id, bank_account_id = self._find_additional_data(cr, uid, currency_code, account_number, context=ctx)
        # Try to find the journal
        journal_id = self._get_journal(cr, uid, currency_id, bank_account_id, account_number, context=ctx)
        # If no journal found, ask the user about creating one
        if not journal_id:
            return self._journal_creation_wizard(cr, uid, currency_id, account_number, bank_account_id, context=ctx)
        # Or directly finish the import
        return self._finalize_import(cr, uid, bank_account_id, account_number, journal_id, stmts_vals, context=ctx)

    def _journal_creation_wizard(self, cr, uid, currency_id, account_number, bank_account_id, context=None):
        """ Calls a wizard that allows the user to accept/refuse journal creation """
        return {
            'name': _('Journal Creation'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.bank.statement.import.journal.creation',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'statement_import_transient_id': context['active_id'],
                'default_currency_id': currency_id,
                'default_account_number': account_number,
                'bank_account_id': bank_account_id,
                'default_name': _('Bank') + ' ' + account_number,
            }
        }

    def _finalize_import(self, cr, uid, bank_account_id, account_number, journal_id, stmts_vals, context=None):
        """ This part is separated from import_file so it can be called via the joutnal creation wizard
            No CUD can happen before this method is called, so not calling it is like aborting the import.
        """
        # Prepare statement data to be used for bank statements creation
        stmts_vals = self._complete_stmts_vals(cr, uid, stmts_vals, journal_id, account_number, context=context)
        # Create the bank statements
        statement_ids, notifications = self._create_bank_statements(cr, uid, stmts_vals, context=context)

        # Finally dispatch to reconciliation interface
        model, action_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'account', 'action_bank_reconcile_bank_statements')
        action = self.pool[model].browse(cr, uid, action_id, context=context)
        return {
            'name': action.name,
            'tag': action.tag,
            'context': {
                'statement_ids': statement_ids,
                'notifications': notifications
            },
            'type': 'ir.actions.client',
        }

    def _parse_file(self, cr, uid, data_file, context=None):
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

    def _check_parsed_data(self, cr, uid, stmts_vals, context=None):
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

    def _find_additional_data(self, cr, uid, currency_code, account_number, context=None):
        """ Get the res.currency ID and the res.partner.bank ID """
        currency_id = False  # So if no currency_code is provided, we'll use the company currency
        if currency_code:
            currency_ids = self.pool.get('res.currency').search(cr, uid, [('name', '=ilike', currency_code)], context=context)
            company_currency_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.currency_id.id
            if currency_ids:
                if currency_ids[0] != company_currency_id:
                    currency_id = currency_ids[0]

        bank_account_id = None
        if account_number and len(account_number) > 4:
            account_number = account_number.replace(' ', '').replace('-', '')
            cr.execute("select id from res_partner_bank where replace(replace(acc_number,' ',''),'-','') = %s", (account_number,))
            bank_account_ids = [id[0] for id in cr.fetchall()]
            bank_account_ids = self.pool.get('res.partner.bank').search(cr, uid, [('id', 'in', bank_account_ids)], context=context)
            if bank_account_ids:
                bank_account_id = bank_account_ids[0]

        return currency_id, bank_account_id

    def _get_journal(self, cr, uid, currency_id, bank_account_id, account_number, context=None):
        """ Find or create the journal """
        bank_pool = self.pool.get('res.partner.bank')

        # Find the journal from context or bank account
        journal_id = context.get('journal_id')
        if bank_account_id:
            bank_account = bank_pool.browse(cr, uid, bank_account_id, context=context)
            if journal_id:
                if bank_account.journal_id.id and bank_account.journal_id.id != journal_id:
                    raise UserError(_('The account of this statement is linked to another journal.'))
                if not bank_account.journal_id.id:
                    bank_pool.write(cr, uid, [bank_account_id], {'journal_id': journal_id}, context=context)
            else:
                if bank_account.journal_id.id:
                    journal_id = bank_account.journal_id.id

        # If importing into an existing journal, its currency must be the same as the bank statement
        if journal_id:
            journal_currency_id = self.pool.get('account.journal').browse(cr, uid, journal_id, context=context).currency.id
            if currency_id and currency_id != journal_currency_id:
                raise UserError(_('The currency of the bank statement is not the same as the currency of the journal !'))

        # If we couldn't find a journal and can't create one, everything is lost
        if not journal_id and not account_number:
            raise UserError(_('Cannot find in which journal import this statement. Please manually select a journal.'))

        return journal_id

    def _create_bank_account(self, cr, uid, account_number, journal_id=False, partner_id=False, context=None):
        try:
            type_model, type_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'base', 'bank_normal')
            type_id = self.pool.get('res.partner.bank.type').browse(cr, uid, type_id, context=context)
            bank_code = type_id.code
        except ValueError:
            bank_code = 'bank'
        account_number = account_number.replace(' ', '').replace('-', '')
        vals_acc = {
            'acc_number': account_number,
            'state': bank_code,
        }
        # Odoo users bank accounts (which we import statement from) have company_id and journal_id set
        # while 'counterpart' bank accounts (from which statement transactions originate) don't.
        # Warning : if company_id is set, the method post_write of class bank will create a journal
        if journal_id:
            vals_acc['partner_id'] = uid
            vals_acc['journal_id'] = journal_id
            vals_acc['company_id'] = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id

        return self.pool.get('res.partner.bank').create(cr, uid, vals_acc, context=context)

    def _complete_stmts_vals(self, cr, uid, stmts_vals, journal_id, account_number, context=None):
        for st_vals in stmts_vals:
            st_vals['journal_id'] = journal_id

            for line_vals in st_vals['transactions']:
                unique_import_id = line_vals.get('unique_import_id', False)
                if unique_import_id:
                    line_vals['unique_import_id'] = (account_number and account_number + '-' or '') + unique_import_id

                if not 'bank_account_id' in line_vals or not line_vals['bank_account_id']:
                    # Find the partner and his bank account or create the bank account. The partner selected during the
                    # reconciliation process will be linked to the bank when the statement is closed.
                    partner_id = False
                    bank_account_id = False
                    identifying_string = line_vals.get('account_number', False)
                    if identifying_string:
                        ids = self.pool.get('res.partner.bank').search(cr, uid, [('acc_number', '=', identifying_string)], context=context)
                        if ids:
                            bank_account_id = ids[0]
                            partner_id = self.pool.get('res.partner.bank').browse(cr, uid, bank_account_id, context=context).partner_id.id
                        else:
                            bank_account_id = self._create_bank_account(cr, uid, identifying_string, context=context)
                    line_vals['partner_id'] = partner_id
                    line_vals['bank_account_id'] = bank_account_id

        return stmts_vals

    def _create_bank_statements(self, cr, uid, stmts_vals, context=None):
        """ Create new bank statements from imported values, filtering out already imported transactions, and returns data used by the reconciliation widget """
        bs_obj = self.pool.get('account.bank.statement')
        bsl_obj = self.pool.get('account.bank.statement.line')

        # Filter out already imported transactions and create statements
        statement_ids = []
        ignored_statement_lines_import_ids = []
        for st_vals in stmts_vals:
            filtered_st_lines = []
            for line_vals in st_vals['transactions']:
                if not 'unique_import_id' in line_vals \
                   or not line_vals['unique_import_id'] \
                   or not bool(bsl_obj.search(cr, SUPERUSER_ID, [('unique_import_id', '=', line_vals['unique_import_id'])], limit=1, context=context)):
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
                statement_ids.append(bs_obj.create(cr, uid, st_vals, context=context))
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
                    'ids': bsl_obj.search(cr, uid, [('unique_import_id', 'in', ignored_statement_lines_import_ids)], context=context)
                }
            }]

        return statement_ids, notifications
