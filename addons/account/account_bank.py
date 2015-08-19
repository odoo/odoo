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

from openerp.tools.translate import _
from openerp.osv import fields, osv

class bank(osv.osv):
    _inherit = "res.partner.bank"
    _columns = {
        'journal_id': fields.many2one('account.journal', 'Account Journal', help="This journal will be created automatically for this bank account when you save the record"),
        'currency_id': fields.related('journal_id', 'currency', type="many2one", relation='res.currency', readonly=True,
            string="Currency", help="Currency of the related account journal."),
    }
    def create(self, cr, uid, data, context=None):
        result = super(bank, self).create(cr, uid, data, context=context)
        self.post_write(cr, uid, [result], context=context)
        return result

    def write(self, cr, uid, ids, data, context=None):
        result = super(bank, self).write(cr, uid, ids, data, context=context)
        self.post_write(cr, uid, ids, context=context)
        return result

    def _prepare_name(self, bank):
        "Return the name to use when creating a bank journal"
        return (bank.bank_name or '') + ' ' + (bank.acc_number or '')

    def _prepare_name_get(self, cr, uid, bank_dicts, context=None):
        """Add ability to have %(currency_name)s in the format_layout of res.partner.bank.type"""
        currency_ids = list(set(data['currency_id'][0] for data in bank_dicts if data.get('currency_id')))
        currencies = self.pool.get('res.currency').browse(cr, uid, currency_ids, context=context)
        currency_name = dict((currency.id, currency.name) for currency in currencies)

        for data in bank_dicts:
            data['currency_name'] = data.get('currency_id') and currency_name[data['currency_id'][0]] or ''
        return super(bank, self)._prepare_name_get(cr, uid, bank_dicts, context=context)

    def post_write(self, cr, uid, ids, context=None):
        if isinstance(ids, (int, long)):
          ids = [ids]

        obj_acc = self.pool.get('account.account')
        obj_data = self.pool.get('ir.model.data')

        for bank in self.browse(cr, uid, ids, context):
            if bank.company_id and not bank.journal_id:
                # Find the code and parent of the bank account to create
                dig = 6
                current_num = 1
                ids = obj_acc.search(cr, uid, [('type','=','liquidity'), ('company_id', '=', bank.company_id.id), ('parent_id', '!=', False)], context=context)
                # No liquidity account exists, no template available
                if not ids: continue

                sibbling_acc_bank = obj_acc.browse(cr, uid, ids[0], context=context)
                ref_acc_bank = sibbling_acc_bank.parent_id
                while True:
                    new_code = str(ref_acc_bank.code.ljust(dig-len(str(current_num)), '0')) + str(current_num)
                    ids = obj_acc.search(cr, uid, [('code', '=', new_code), ('company_id', '=', bank.company_id.id)])
                    if not ids:
                        break
                    current_num += 1
                name = self._prepare_name(bank)
                acc = {
                    'name': name,
                    'code': new_code,
                    'type': 'liquidity',
                    'user_type': sibbling_acc_bank.user_type.id,
                    'reconcile': False,
                    'parent_id': ref_acc_bank.id,
                    'company_id': bank.company_id.id,
                }
                acc_bank_id  = obj_acc.create(cr,uid,acc,context=context)

                jour_obj = self.pool.get('account.journal')
                new_code = 1
                while True:
                    code = _('BNK')+str(new_code)
                    ids = jour_obj.search(cr, uid, [('code','=',code)], context=context)
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
                journal_id = jour_obj.create(cr, uid, vals_journal, context=context)

                self.write(cr, uid, [bank.id], {'journal_id': journal_id}, context=context)
        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
