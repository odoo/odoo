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
        'my_bank': fields.boolean('Use my account to print BVR ?', help="Check to print BVR invoices"),
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

    def _prepare_name(self, bank):
        "Hook to get bank number of bank account"
        res = super(ResPartnerBank, self)._prepare_name(bank)
        if bank.post_number:
            res =  u"%s - %s" % (res, bank.post_number)
        return res

    _sql_constraints = [('bvr_adherent_uniq', 'unique (bvr_adherent_num)',
        'The BVR adherent number must be unique !')]

ResPartnerBank()
