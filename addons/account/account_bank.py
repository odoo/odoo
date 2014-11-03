# -*- coding: utf-8 -*-

from openerp import models, fields, api, _

class bank(models.Model):
    _inherit = "res.partner.bank"

    journal_id = fields.Many2one('account.journal', string='Account Journal', 
        help="This journal will be created automatically for this bank account when you save the record")
    currency_id = fields.Many2one('res.currency', related='journal_id.currency', string='Currency',
        readonly=True, help="Currency of the related account journal.")

    @api.model
    def create(self, data):
        result = super(bank, self).create(data)
        result.post_write()
        return result

    @api.multi
    def write(self, data):
        result = super(bank, self).write(data)
        self.post_write()
        return result

    @api.model
    def _prepare_name(self, bank):
        "Return the name to use when creating a bank journal"
        return (bank.bank_name or '') + ' ' + (bank.acc_number or '')

    @api.model
    def _prepare_name_get(self, bank_dicts):
        """Add ability to have %(currency_name)s in the format_layout of res.partner.bank.type"""
        currency_ids = list(set(data['currency_id'][0] for data in bank_dicts if data.get('currency_id')))
        currencies = self.env['res.currency'].browse(currency_ids)
        currency_name = dict((currency.id, currency.name) for currency in currencies)

        for data in bank_dicts:
            data['currency_name'] = data.get('currency_id') and currency_name[data['currency_id'][0]] or ''
        return super(bank, self)._prepare_name_get(bank_dicts)

    @api.multi
    def post_write(self):
        AccountObj = self.env['account.account']
        JournalObj = self.env['account.journal']

        for bank in self:
            if bank.company_id and not bank.journal_id:
                # Find the code and parent of the bank account to create
                dig = 6
                current_num = 1
                account = AccountObj.search([('type','=','liquidity'), ('company_id', '=', bank.company_id.id)], limit=1)
                # No liquidity account exists, no template available
                if not account: continue

                ref_acc_bank = account
                while True:
                    new_code = str(ref_acc_bank.code.ljust(dig-len(str(current_num)), '0')) + str(current_num)
                    account = AccountObj.search([('code', '=', new_code), ('company_id', '=', bank.company_id.id)], limit=1)
                    if not account:
                        break
                    current_num += 1
                name = self._prepare_name(bank)
                acc = {
                    'name': name,
                    'code': new_code,
                    'type': 'liquidity',
                    'user_type': ref_acc_bank.user_type.id,
                    'reconcile': False,
                    'company_id': bank.company_id.id,
                }
                acc_bank_id  = AccountObj.create(acc)

                new_code = 1
                while True:
                    code = _('BNK')+str(new_code)
                    account = JournalObj.search([('code','=',code)], limit=1)
                    if not account:
                        break
                    new_code += 1

                #create the bank journal
                vals_journal = {
                    'name': name,
                    'code': code,
                    'type': 'bank',
                    'company_id': bank.company_id.id,
                    'analytic_journal_id': False,
                    'default_credit_account_id': acc_bank_id,
                    'default_debit_account_id': acc_bank_id,
                }

                bank.journal_id = JournalObj.create(vals_journal)
        return True
