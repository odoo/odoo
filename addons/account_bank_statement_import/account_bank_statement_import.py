# -*- coding: utf-8 -*-

import base64

from openerp.osv import fields, osv
from openerp.tools.translate import _

import logging
_logger = logging.getLogger(__name__)

class account_bank_statement_import(osv.TransientModel):
    _name = 'account.bank.statement.import'
    _description = 'Import Bank Statement'

    _columns = {
        'data_file': fields.binary('Bank Statement File', required=True, help='Get you bank statements in electronic format from your bank and select them here.'),
        'journal_id': fields.many2one('account.journal', 'Journal', required=True, help="The journal for which the bank statements will be created"),
        'hide_journal_field': fields.boolean('Hide the journal field in the view'),
    }

    def _get_default_journal(self, cr, uid, context=None):
        if 'journal_id' in context:
            return context['journal_id']
        company_id = self.pool.get('res.company')._company_default_get(cr, uid, 'account.bank.statement', context=context)
        journal_ids = self.pool.get('account.journal').search(cr, uid, [('type', '=', 'bank'), ('company_id', '=', company_id)], context=context)
        return journal_ids and journal_ids[0] or False

    def _get_hide_journal_field(self, cr, uid, context=None):
        return 'journal_id' in context

    _defaults = {
        'journal_id': _get_default_journal,
        'hide_journal_field': _get_hide_journal_field,
    }

    def _handle_account_number(self, cr, uid, journal_id, acc_number, context=None):
        """ Create a new bank account or set its journal_id or check its journal_id is the same we're importing into """
        if not acc_number or acc_number == '':
            return
        bank_pool = self.pool.get('res.partner.bank')
        acc_number = acc_number.replace(' ','').replace('-','')
        # Find bank account corresponding to the acc_number
        cr.execute("select id from res_partner_bank where replace(replace(acc_number,' ',''),'-','') = %s", (acc_number,))
        bank_ids = [id[0] for id in cr.fetchall()]
        bank_ids = bank_pool.search(cr, uid, [('id', 'in', bank_ids)], context=context)
        # If it exists, either it has a journal_id which needs to be the same we're importing in or it doesn't and we set it
        if bank_ids and len(bank_ids) > 0:
            bank_acc = bank_pool.browse(cr, uid, bank_ids[0], context=context)
            if bank_acc.journal_id.id and bank_acc.journal_id.id != journal_id:
                raise osv.except_osv(_('Error'), _('The account of this statement is linked to another journal.'))
            if not bank_acc.journal_id.id:
                bank_pool.write(cr, uid, [bank_ids[0]], {'journal_id': journal_id}, context=context)
        # Or create it
        else:
            try:
                type_model, type_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'base', 'bank_normal')
                type_id = self.pool.get('res.partner.bank.type').browse(cr, uid, type_id, context=context)
                bank_code = type_id.code
            except ValueError:
                bank_code = 'bank'
            vals = {
                'acc_number': acc_number,
                'state': bank_code,
                'partner_id': uid,
                'journal_id': journal_id,
            }
            bank_pool.create(cr, uid, vals, context=context)

    def _detect_partner(self, cr, uid, identifying_string, identifying_field='acc_number', context=None):
        """Try to find a bank account and its related partner for the given 'identifying_string', looking on the field 'identifying_field'.

           :param identifying_string: varchar
           :param identifying_field: varchar corresponding to the name of a field of res.partner.bank
           :returns: tuple(ID of the bank account found or False, ID of the partner for the bank account found or False)
        """
        partner_id = False
        bank_account_id = False
        if identifying_string:
            ids = self.pool.get('res.partner.bank').search(cr, uid, [(identifying_field, '=', identifying_string)], context=context)
            if ids:
                bank_account_id = ids[0]
                partner_id = self.pool.get('res.partner.bank').browse(cr, uid, bank_account_id, context=context).partner_id.id
            else:
                #create the bank account, not linked to any partner. The reconciliation will link the partner manually
                #chosen at the bank statement final confirmation time.
                try:
                    type_model, type_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'base', 'bank_normal')
                    type_id = self.pool.get('res.partner.bank.type').browse(cr, uid, type_id, context=context)
                    bank_code = type_id.code
                except ValueError:
                    bank_code = 'bank'
                if identifying_field == 'acc_number' and identifying_string:
                    bank_account_vals = {
                        'acc_number': identifying_string.replace(' ','').replace('-',''),
                        'state': bank_code,
                    }
                    bank_account_id = self.pool.get('res.partner.bank').create(cr, uid, bank_account_vals, context=context)
        return bank_account_id, partner_id

    def import_bank_statements(self, cr, uid, bank_statement_vals=False, context=None):
        """ Create new bank statements from imported values, filtering out already imported transactions, and returns data used by the reconciliation widget """
        bs_obj = self.pool.get('account.bank.statement')
        if len(bank_statement_vals) == 0:
            raise osv.except_osv(_('Error'), _('The file doesn\'t contain any bank statement (or wasn\'t properly processed).'))
        
        # Filter out already imported transactions and create statements
        statement_ids = []
        num_ignored_statement_lines = 0
        cr.execute("SELECT unique_import_id FROM account_bank_statement_line")
        already_imported_lines = [x[0] for x in cr.fetchall()]
        for st_vals in bank_statement_vals:
            filtered_st_lines = []
            for line_vals in st_vals['line_ids']:
                if not 'unique_import_id' in line_vals[2] or line_vals[2]['unique_import_id'] not in already_imported_lines:
                    filtered_st_lines.append(line_vals)
                else:
                    num_ignored_statement_lines += 1
            if len(filtered_st_lines) > 0:
                st_vals['line_ids'] = filtered_st_lines
                statement_ids.append(bs_obj.create(cr, uid, st_vals, context=context))
        if len(statement_ids) == 0:
            raise osv.except_osv(_('Error'), _('You have already imported that file.'))

        # Prepare import feedback
        notifications = []
        if num_ignored_statement_lines > 1:
            notifications += [{
                'type': 'warning', # note : can be success, info, warning or danger
                'message': _("%d transactions had already been imported and were ignored.") % num_ignored_statement_lines
            }]

        return statement_ids, notifications

    # Each module adding a file support must extends this method. It processes the file if it can, returns super otherwise, resulting in a chain of responsability
    def _process_file(self, cr, uid, data_file=None, journal_id=False, context=None):
        raise osv.except_osv(_('Error'), _('Could not make sense of the given file.\nDid you install the module to support this type of file ?'))


    def parse_file(self, cr, uid, ids, context=None):
        """ Process the file chosen in the wizard, create bank statement(s) and go to reconciliation. """
        data = self.browse(cr, uid, ids[0], context=context)
        
        vals = self._process_file(cr, uid, base64.b64decode(data.data_file), data.journal_id.id, context=context)
        self._handle_account_number(cr, uid, data.journal_id.id, vals['account_number'])
        statement_ids, notifications = self.import_bank_statements(cr, uid, vals['bank_statement_vals'], context=context)
        
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

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
