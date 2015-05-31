# -*- coding: utf-8 -*-

from openerp import api, fields, models

class account_bank_statement_import_journal_creation(models.TransientModel):
    _name = 'account.bank.statement.import.journal.creation'
    _description = 'Import Bank Statement Journal Creation Wizard'

    name = fields.Char('Journal Name', required=True)
    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True)
    account_number = fields.Char('Account Number', readonly=True)

    @api.multi
    def create_journal(self):
        import_wiz_obj = self.env['account.bank.statement.import']
        journal_obj = self.env['account.journal']
        company = self.env.user.company_id
        wiz = self[0]
        currency_id = wiz.currency_id.id
        account_number = wiz.account_number

        bank_account_id = self.env.context.get('bank_account_id')
        if bank_account_id:
            vals = {'currency_id': currency_id, 'acc_name': account_number, 'account_type': 'bank'}
            vals_journal = journal_obj._prepare_bank_journal(company, vals)
            journal = journal_obj.create(vals_journal)
            self.env['res.partner.bank'].browse(bank_account_id).write({'journal_id': journal.id})
        else:
            #create the bank account that will trigger the journal and account.account creation
            res_partner_bank_vals = {
                    'acc_number': account_number,
                    'currency_id': currency_id,
                    'company_id': company.id,
                    'owner_name': company.partner_id.name,
                    'partner_id': company.partner_id.id,
                    'footer': True
            }
            self.env['res.partner.bank'].create(res_partner_bank_vals)

        # Finish the statement import
        statement_import_transient = import_wiz_obj.browse(self.env.context['statement_import_transient_id'])
        return statement_import_transient.import_file()
