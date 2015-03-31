# -*- coding: utf-8 -*-

from openerp.osv import fields, osv
from openerp.tools.translate import _

class account_bank_statement_import_journal_creation(osv.TransientModel):
    _name = 'account.bank.statement.import.journal.creation'
    _description = 'Import Bank Statement Journal Creation Wizard'
    _columns = {
        'name': fields.char('Journal Name', required=True),
        'currency_id': fields.many2one('res.currency', 'Currency', readonly=True),
        'account_number': fields.char('Account Number', readonly=True),
    }

    def create_journal(self, cr, uid, ids, context=None):
        bank_account_id = context['bank_account_id']

        wmca_pool = self.pool.get('wizard.multi.charts.accounts')
        company = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id
        currency_id = context['currency_id']
        account_number = context['account_number']

        # Create the account.account
        vals_account = {'currency_id': currency_id, 'acc_name': account_number, 'account_type': 'bank', 'currency_id': currency_id}
        vals_account = wmca_pool._prepare_bank_account(cr, uid, company, vals_account, context=context)
        account_id = self.pool.get('account.account').create(cr, uid, vals_account, context=context)

        # Create the account.journal
        name = self.browse(cr, uid, ids, context=context)[0].name
        vals_journal = {'currency_id': currency_id, 'acc_name': name, 'account_type': 'bank'}
        vals_journal = wmca_pool._prepare_bank_journal(cr, uid, company, vals_journal, account_id, context=context)
        journal_id = self.pool.get('account.journal').create(cr, uid, vals_journal, context=context)
        if bank_account_id:
            self.pool.get('res.partner.bank').write(cr, uid, [bank_account_id], {'journal_id': journal_id}, context=context)

        # Finish the statement import
        statement_import_transient = self.pool.get('account.bank.statement.import').browse(cr, uid, context['statement_import_transient_id'], context=context)
        return statement_import_transient.import_file()
