# -*- coding: utf-8 -*-

import base64

from openerp import SUPERUSER_ID
from openerp.osv import fields, osv
from openerp.tools.translate import _

import logging
_logger = logging.getLogger(__name__)

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
        data_file = self.browse(cr, uid, ids[0], context=context).data_file

        # The appropriate implementation module returns the required data
        currency_code, account_number, stmts_vals = self._parse_file(cr, uid, base64.b64decode(data_file), context=context)
        # Check raw data
        self._check_parsed_data(cr, uid, stmts_vals, context=context)
        # Try to find the bank account and currency in odoo
        currency_id, bank_account_id = self._find_additional_data(cr, uid, currency_code, account_number, context=context)
        # Find or create the bank journal
        journal_id = self._get_journal(cr, uid, currency_id, bank_account_id, account_number, context=context)
        # Create the bank account if not already existing
        if not bank_account_id and account_number:
            self._create_bank_account(cr, uid, account_number, journal_id=journal_id, partner_id=uid, context=context)
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

    def _parse_file(self, cr, uid, data_file=None, context=None):
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
        raise osv.except_osv(_('Error'), _('Could not make sense of the given file.\nDid you install the module to support this type of file ?'))

    def _check_parsed_data(self, cr, uid, stmts_vals, context=None):
        """ Basic and structural verifications """
        if len(stmts_vals) == 0:
            raise osv.except_osv(_('Error'), _('This file doesn\'t contain any statement.'))
        
        no_st_line = True
        for vals in stmts_vals:
            if vals['transactions'] and len(vals['transactions']) > 0:
                no_st_line = False
                break
        if no_st_line:
            raise osv.except_osv(_('Error'), _('This file doesn\'t contain any transaction.'))

    def _find_additional_data(self, cr, uid, currency_code, account_number, context=None):
        """ Get the res.currency ID and the res.partner.bank ID """
        currency_id = False # So if no currency_code is provided, we'll use the company currency
        if currency_code:
            currency_ids = self.pool.get('res.currency').search(cr, uid, [('name', '=ilike', currency_code)], context=context)
            company_currency_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.currency_id.id
            if currency_ids:
                if currency_ids[0] != company_currency_id:
                    currency_id = currency_ids[0]

        bank_account_id = None
        if account_number and len(account_number) > 4:
            account_number = account_number.replace(' ','').replace('-','')
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
                    raise osv.except_osv(_('Error'), _('The account of this statement is linked to another journal.'))
                if not bank_account.journal_id.id:
                    bank_pool.write(cr, uid, [bank_account_id], {'journal_id': journal_id}, context=context)
            else:
                if bank_account.journal_id.id:
                    journal_id = bank_account.journal_id.id

        # If importing into an existing journal, its currency must be the same as the bank statement
        if journal_id:
            journal_currency_id = self.pool.get('account.journal').browse(cr, uid, journal_id, context=context).currency.id
            if currency_id and currency_id != journal_currency_id:
                raise osv.except_osv(_('Error'), _('The currency of the bank statement is not the same as the currency of the journal !'))

        # If there is no journal, create one (and its account)
        if not journal_id and account_number:
            journal_id = self._create_journal(cr, uid, currency_id, account_number, context=context)
            if bank_account_id:
                bank_pool.write(cr, uid, [bank_account_id], {'journal_id': journal_id}, context=context)

        # If we couldn't find/create a journal, everything is lost
        if not journal_id:
            raise osv.except_osv(_('Error'), _('Cannot find in which journal import this statement. Please open this wizard from a journal.'))

        return journal_id

    def _create_journal(self, cr, uid, currency_id, account_number, context=None):
        """ Create a journal and its account """
        wmca_pool = self.pool.get('wizard.multi.charts.accounts')
        company = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id
        
        vals_account = {'currency_id': currency_id, 'acc_name': account_number, 'account_type': 'bank', 'currency_id': currency_id }
        vals_account = wmca_pool._prepare_bank_account(cr, uid, company, vals_account, context=context)
        account_id = self.pool.get('account.account').create(cr, uid, vals_account, context=context)
        
        vals_journal = {'currency_id': currency_id, 'acc_name': _('Bank') + ' ' + account_number, 'account_type': 'bank' }
        vals_journal = wmca_pool._prepare_bank_journal(cr, uid, company, vals_journal, account_id, context=context)
        return self.pool.get('account.journal').create(cr, uid, vals_journal, context=context)

    def _create_bank_account(self, cr, uid, account_number, journal_id=False, partner_id=False, context=None):
        try:
            type_model, type_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'base', 'bank_normal')
            type_id = self.pool.get('res.partner.bank.type').browse(cr, uid, type_id, context=context)
            bank_code = type_id.code
        except ValueError:
            bank_code = 'bank'
        account_number = account_number.replace(' ','').replace('-','')
        vals_acc = {
            'acc_number': account_number,
            'state': bank_code,
            'partner_id': uid,
            'journal_id': journal_id,
        }
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
                st_vals['line_ids'] = [[0, False, line] for line in filtered_st_lines]
                statement_ids.append(bs_obj.create(cr, uid, st_vals, context=context))
        if len(statement_ids) == 0:
            raise osv.except_osv(_('Error'), _('You have already imported that file.'))

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

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: