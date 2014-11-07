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
        data_file = self.browse(cr, uid, ids[0], context=context).data_file
        
        vals = self._parse_file(cr, uid, base64.b64decode(data_file), context=context)
        self._complete_data(cr, uid, vals, context=context)
        self._check_data(cr, uid, vals, context=context)
        statement_ids, notifications = self._create_bank_statements(cr, uid, vals, context=context)
        
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

    # Each module adding a file support must extends this method. It processes the file if it can, returns super otherwise, resulting in a chain of responsability
    def _parse_file(self, cr, uid, data_file=None, context=None):
        raise osv.except_osv(_('Error'), _('Could not make sense of the given file.\nDid you install the module to support this type of file ?'))

    def _detect_partner(self, cr, uid, identifying_string, identifying_field='acc_number', context=None):
        """Try to find a bank account and its related partner for the given 'identifying_string', looking on the field 'identifying_field'.

           :param identifying_string: varchar
           :param identifying_field: varchar corresponding to the name of a field of res.partner.bank
           :returns: tuple(ID of the bank account found or False, ID of the partner for the bank account found or False)
        """
        partner_id = False
        bank_account_id = False
        if identifying_string:
            # Get the partner_id and his bank_account_id
            ids = self.pool.get('res.partner.bank').search(cr, uid, [(identifying_field, '=', identifying_string)], context=context)
            if ids:
                bank_account_id = ids[0]
                partner_id = self.pool.get('res.partner.bank').browse(cr, uid, bank_account_id, context=context).partner_id.id
            # Or create the bank account, not linked to any partner. The reconciliation will link the partner
            # manually chosen at the bank statement final confirmation time.
            elif identifying_field == 'acc_number' and identifying_string:
                try:
                    type_model, type_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'base', 'bank_normal')
                    type_id = self.pool.get('res.partner.bank.type').browse(cr, uid, type_id, context=context)
                    bank_code = type_id.code
                except ValueError:
                    bank_code = 'bank'
                bank_account_vals = {
                    'acc_number': identifying_string.replace(' ','').replace('-',''),
                    'state': bank_code,
                }
                bank_account_id = self.pool.get('res.partner.bank').create(cr, uid, bank_account_vals, context=context)
        return bank_account_id, partner_id

    def _complete_data(self, cr, uid, vals, context=None):
        """ Get the journal_id and if necessary create bank account / journal """
        wmca_pool = self.pool.get('wizard.multi.charts.accounts')
        bank_pool = self.pool.get('res.partner.bank')

        # Find currency
        vals['currency_id'] = False
        if 'currency_code' in vals:
            currency_ids = self.pool.get('res.currency').search(cr, uid, [('name', 'ilike', vals['currency_code'])], context=context)
            company_currency_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.currency_id.id
            if currency_ids and currency_ids[0] != company_currency_id:
                vals['currency_id'] = currency_ids[0]

        # Handle account and journal
        if not 'account_number' in vals or not vals['account_number'] or len(vals['account_number']) < 4:
            return
        acc_number = vals['account_number'].replace(' ','').replace('-','')
        vals['journal_id'] = 'journal_id' in context and context['journal_id'] or False
        
        # Find bank account corresponding to the acc_number
        cr.execute("select id from res_partner_bank where replace(replace(acc_number,' ',''),'-','') = %s", (acc_number,))
        bank_ids = [id[0] for id in cr.fetchall()]
        bank_ids = bank_pool.search(cr, uid, [('id', 'in', bank_ids)], context=context)
        
        # If the bank account exists, check its journal
        bank_id = bank_ids and bank_ids[0] or False
        if bank_id:
            bank_acc = bank_pool.browse(cr, uid, bank_id, context=context)
            if vals['journal_id']:
                if bank_acc.journal_id.id and bank_acc.journal_id.id != vals['journal_id']:
                    raise osv.except_osv(_('Error'), _('The account of this statement is linked to another journal.'))
                if not bank_acc.journal_id.id:
                    bank_pool.write(cr, uid, [bank_id], {'journal_id': vals['journal_id']}, context=context)
            else:
                if bank_acc.journal_id.id:
                    vals['journal_id'] = bank_acc.journal_id.id

        # If there is no journal, create one (and its account)
        if not vals['journal_id']:
            company = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id
            vals_account = {'currency_id': vals['currency_id'], 'acc_name': acc_number, 'account_type': 'bank', 'currency_id': vals['currency_id'] }
            vals_account = wmca_pool._prepare_bank_account(cr, uid, company, vals_account, context=context)
            account_id = self.pool.get('account.account').create(cr, uid, vals_account, context=context)
            vals_journal = {'currency_id': vals['currency_id'], 'acc_name': _('Bank') + ' ' + acc_number, 'account_type': 'bank' }
            vals_journal = wmca_pool._prepare_bank_journal(cr, uid, company, vals_journal, account_id, context=context)
            vals['journal_id'] = self.pool.get('account.journal').create(cr, uid, vals_journal, context=context)
            if bank_id:
                bank_pool.write(cr, uid, [bank_id], {'journal_id': vals['journal_id']}, context=context)

        # If there is no bank account, create one
        if not bank_id:
            try:
                type_model, type_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'base', 'bank_normal')
                type_id = self.pool.get('res.partner.bank.type').browse(cr, uid, type_id, context=context)
                bank_code = type_id.code
            except ValueError:
                bank_code = 'bank'
            vals_acc = {
                'acc_number': acc_number,
                'state': bank_code,
                'partner_id': uid,
                'journal_id': vals['journal_id'],
            }
            bank_pool.create(cr, uid, vals_acc, context=context)

        # Complete bank statements and bank statement lines vals
        for st_vals in vals['bank_statement_vals']:
            if 'journal_id' in vals:
                st_vals['journal_id'] = vals['journal_id']

            for line_vals in st_vals['line_ids']:
                if 'unique_import_id' in line_vals and line_vals['unique_import_id']:
                    line_vals['unique_import_id'] = acc_number + '-' + line_vals['unique_import_id']

        # TODO : find period_id
        # see https://gist.github.com/Whisno/313081bbdc08668f5a23

        # Remove values which are not account.statement.line columns
        vals.pop("statement_start_date", None)
        vals.pop("statement_end_date", None)

    def _check_data(self, cr, uid, vals, context=None):
        """ Verify that the data we retrieved is suitable """
        
        if not 'journal_id' in vals or not vals['journal_id']:
            raise osv.except_osv(_('Error'), _('Cannot find in which journal import this statement. Please open this wizard from a journal.'))

        journal_currency_id = self.pool.get('account.journal').browse(cr, uid, vals['journal_id'], context=context).currency.id
        if 'currency_id' in vals and vals['currency_id'] != journal_currency_id:
            raise osv.except_osv(_('Error'), _('The currency of the bank statement is not the same as the currency of the journal !'))

        if len(vals['bank_statement_vals']) == 0:
            raise osv.except_osv(_('Error'), _('This file doesn\'t contain any statement.'))
        
        no_st_line = True
        for st_vals in vals['bank_statement_vals']:
            if st_vals['line_ids'] and len(st_vals['line_ids']) > 0:
                no_st_line = False
        if no_st_line:
            raise osv.except_osv(_('Error'), _('This file doesn\'t contain any transaction.'))

        # TODO : check period_id exists and check there's no gap between last statement and this one
        # see https://gist.github.com/Whisno/313081bbdc08668f5a23

    def _create_bank_statements(self, cr, uid, vals, context=None):
        """ Create new bank statements from imported values, filtering out already imported transactions, and returns data used by the reconciliation widget """
        bs_obj = self.pool.get('account.bank.statement')
        bsl_obj = self.pool.get('account.bank.statement.line')

        # Filter out already imported transactions and create statements
        statement_ids = []
        ignored_statement_lines_import_ids = []
        for st_vals in vals['bank_statement_vals']:
            filtered_st_lines = []
            for line_vals in st_vals['line_ids']:
                if not 'unique_import_id' in line_vals \
                   or not line_vals['unique_import_id'] \
                   or not bool(bsl_obj.search(cr, SUPERUSER_ID, [('unique_import_id', '=', line_vals['unique_import_id'])], context=context)):
                    filtered_st_lines.append(line_vals)
                else:
                    ignored_statement_lines_import_ids.append(line_vals['unique_import_id'])
            if len(filtered_st_lines) > 0:
                st_vals['line_ids'] = filtered_st_lines
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
                    'ids': bsl_obj.search(cr, uid, ['&', ('unique_import_id', 'in', ignored_statement_lines_import_ids), ('journal_id', '=', vals['journal_id'])], context=context)
                }
            }]

        return statement_ids, notifications

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
