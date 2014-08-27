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
    }

    def _get_default_journal(self, cr, uid, context=None):
        company_id = self.pool.get('res.company')._company_default_get(cr, uid, 'account.bank.statement', context=context)
        journal_ids = self.pool.get('account.journal').search(cr, uid, [('type', '=', 'bank'), ('company_id', '=', company_id)], context=context)
        return journal_ids and journal_ids[0] or False

    _defaults = {
        'journal_id': _get_default_journal,
    }

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
                acc_number = identifying_field == 'acc_number' and identifying_string or _('Undefined')
                bank_account_vals = {
                    'acc_number': acc_number,
                    'state': bank_code,
                }
                bank_account_vals[identifying_field] = identifying_string
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
            num_ignored_statement_lines += len(st_vals['line_ids'])
            st_vals['line_ids'] = [line_vals for line_vals in st_vals['line_ids'] if line_vals[2]['unique_import_id'] not in already_imported_lines]
            num_ignored_statement_lines -= len(st_vals['line_ids'])
            if len(st_vals['line_ids']) > 0:
                statement_ids.append(bs_obj.create(cr, uid, st_vals, context=context))
        if len(statement_ids) == 0:
            raise osv.except_osv(_('Error'), _('You have already imported that file.'))

        # Prepare import feedback
        notifications = []
        if num_ignored_statement_lines > 1:
            notifications += [{
                'type': 'warning', # note : can be success, info, warning or danger
                'message': _("%d transactions had already been imported and therefore were ignored. You might want to check how your bank exports statements.") % num_ignored_statement_lines
            }]

        return statement_ids, notifications

    # Each module adding a file support must extends this method. It processes the file if it can, returns super otherwise, resulting in a chain of responsability
    def _process_file(self, cr, uid, data_file=None, journal_id=False, context=None):
        raise osv.except_osv(_('Error'), _('Could not make sense of the given file.\nDid you install the module to support this type of file ?'))


    def parse_file(self, cr, uid, ids, context=None):
        """ Process the file chosen in the wizard, create bank statement(s) and go to reconciliation. """
        data = self.browse(cr, uid, ids[0], context=context)
        vals = self._process_file(cr, uid, base64.b64decode(data.data_file), data.journal_id.id, context=context)
        statement_ids, notifications = self.import_bank_statements(cr, uid, vals, context=context)
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
