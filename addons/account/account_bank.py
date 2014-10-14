# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import models, fields, api, _

class bank(models.Model):
    _inherit = "res.partner.bank"

    journal_id = fields.Many2one('account.journal', string='Account Journal', help="This journal will be created automatically for this bank account when you save the record")
    currency_id = fields.Many2one('res.currency', related='journal_id', string='Currency', readonly=True, help="Currency of the related account journal.")

    @api.model
    @api.returns('self')
    def create(self, data):
        result = super(bank, self).create(data)
        self.post_write([result])
        return result

    @api.multi
    def write(self, data):
        result = super(bank, self).write(data)
        self.post_write(ids)
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
                ids = AccountObj.search([('type','=','liquidity'), ('company_id', '=', bank.company_id.id)])
                # No liquidity account exists, no template available
                if not ids: continue

                ref_acc_bank = ids[0]
                while True:
                    new_code = str(ref_acc_bank.code.ljust(dig-len(str(current_num)), '0')) + str(current_num)
                    ids = AccountObj.search([('code', '=', new_code), ('company_id', '=', bank.company_id.id)])
                    if not ids:
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
                    ids = JournalObj.search([('code','=',code)])
                    if not ids:
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
                journal_id = JournalObj.create(vals_journal)

                bank.write({'journal_id': journal_id})
        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
