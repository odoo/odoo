# -*- encoding: utf-8 -*-
##############################################################################
#
#    Author: Nicolas Bessi. Copyright Camptocamp SA
#    Donors: Hasa Sàrl, Open Net Sàrl and Prisme Solutions Informatique SA
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

from tools.translate import _
from osv import fields, osv

class Bank(osv.osv):
    """Inherit res.bank class in order to add swiss specific field"""
    _inherit = 'res.bank'
    _columns = {
        ### Internal reference
        'code': fields.char('Code', size=64),
        ###Swiss unik bank identifier also use in IBAN number
        'clearing': fields.char('Clearing number', size=64),
        ### city of the bank
        'city': fields.char('City', size=128, select=1),
    }

Bank()


class ResPartnerBank(osv.osv):
    _inherit = "res.partner.bank"

    _columns = {
        'name': fields.char('Description', size=128, required=True),
        'post_number': fields.char('Post number', size=64),
        'bvr_adherent_num': fields.char('BVR adherent number', size=11),
        'dta_code': fields.char('DTA code', size=5),
        'print_bank': fields.boolean('Print Bank on BVR'),
        'print_account': fields.boolean('Print Account Number on BVR'),
        'acc_number': fields.char('Account/IBAN Number', size=64),
     
    }

    def name_get(self, cursor, uid, ids, context=None):
        if not len(ids):
            return []
        bank_type_obj = self.pool.get('res.partner.bank.type')

        type_ids = bank_type_obj.search(cursor, uid, [])
        bank_type_names = {}
        for bank_type in bank_type_obj.browse(cursor, uid, type_ids,
                context=context):
            bank_type_names[bank_type.code] = bank_type.name
        res = []
        for r in self.read(cursor, uid, ids, ['name','state'], context):
            res.append((r['id'], r['name']+' : '+bank_type_names.get(r['state'], '')))
        return res        
    
    def post_write(self, cr, uid, ids, context={}):
        """ Override of post_write method.
            In Switzerland with post accounts you can either have a postal account
            with a required bank number (BVR Bank) or a postal number alone (BV Post, BVR Post).
            So acc_number is not always mandatory and postal and bank number are not the same field """ 
        
        obj_acc = self.pool.get('account.account')
        obj_data = self.pool.get('ir.model.data')
        for bank in self.browse(cr, uid, ids, context):
            if bank.company_id and not bank.journal_id:
                # Find the code and parent of the bank account to create
                dig = 6
                current_num = 1
                ids = obj_acc.search(cr, uid, [('type','=','liquidity')], context=context)
                # No liquidity account exists, no template available
                if not ids: continue

                ref_acc_bank_temp = obj_acc.browse(cr, uid, ids[0], context=context)
                ref_acc_bank = ref_acc_bank_temp.parent_id
                while True:
                    new_code = str(ref_acc_bank.code.ljust(dig-len(str(current_num)), '0')) + str(current_num)
                    ids = obj_acc.search(cr, uid, [('code', '=', new_code), ('company_id', '=', bank.company_id.id)])
                    if not ids:
                        break
                    current_num += 1
                
                # Here is the test
                if not bank.acc_number:
                    number = bank.post_number
                else:
                    number = bank.acc_number

                acc = {
                    'name': (bank.bank_name or '')+' '+ number,
                    'currency_id': bank.company_id.currency_id.id,
                    'code': new_code,
                    'type': 'liquidity',
                    'user_type': ref_acc_bank_temp.user_type.id,
                    'reconcile': False,
                    'parent_id': ref_acc_bank.id,
                    'company_id': bank.company_id.id,
                }
                acc_bank_id  = obj_acc.create(cr,uid,acc,context=context)

                # Get the journal view id
                data_id = obj_data.search(cr, uid, [('model','=','account.journal.view'), ('name','=','account_journal_bank_view')])
                data = obj_data.browse(cr, uid, data_id[0], context=context)
                view_id_cash = data.res_id

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
                    'name':  (bank.bank_name or '')+' '+number,
                    'code': code,
                    'type': 'bank',
                    'company_id': bank.company_id.id,
                    'analytic_journal_id': False,
                    'currency_id': False,
                    'default_credit_account_id': acc_bank_id,
                    'default_debit_account_id': acc_bank_id,
                    'view_id': view_id_cash
                }
                journal_id = jour_obj.create(cr, uid, vals_journal, context=context)

                self.write(cr, uid, [bank.id], {'journal_id': journal_id}, context=context)
        return True
   

    _sql_constraints = [('bvr_adherent_uniq', 'unique (bvr_adherent_num)',
        'The BVR adherent number must be unique !')]

ResPartnerBank()
