# -*- coding: utf-8 -*-
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

from osv import fields, osv
from tools import mod10r
import re

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


class ResPartnerBank(osv.osv):
    """
    Inherit res.partner.bank class in order to add swiss specific fields
    such as:
     - A postnumber
     - BVR data
     - BVR print options for company accounts
    """
    _inherit = "res.partner.bank"

    _columns = {
        'name': fields.char('Description', size=128, required=True),
        'post_number': fields.char('Post number', size=64, help="Postal number 0x-xxxxxx-x or xxxxx"),
        'bvr_adherent_num': fields.char('Bank BVR adherent number', size=11, help="Your Bank adherent number to be printed in references of your BVR. This is not a postal account number."),
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
        res = u''
        if bank.acc_number:
            res = super(ResPartnerBank, self)._prepare_name(bank) or u''
        if bank.post_number:
            if res:
                res =  u"%s - %s" % (res, bank.post_number)
            else:
                res = bank.post_number
        return res

    def _check_9_pos_postal_num(self, number):
        """
        check if a postal number in format xx-xxxxxx-x is correct,
        return true if it matches the pattern
        and if check sum mod10 is ok
        """
        pattern = r'^[0-9]{2}-[0-9]{1,6}-[0-9]$'
        if not re.search(pattern, number):
            return False
        nums = number.split('-')
        prefix = nums[0]
        num = nums[1].rjust(6,'0')
        checksum = nums[2]
        expected_checksum = mod10r(prefix + num)[-1]
        return expected_checksum == checksum


    def _check_5_pos_postal_num(self, number):
        """
        check if a postal number on 5 positions is correct
        """
        pattern = r'^[0-9]{1,5}$'
        if not re.search(pattern, number):
            return False
        return True

    def _check_postal_num(self, cursor, uid, ids):
        """
        validate postal number format
        """
        banks = self.browse(cursor, uid, ids)
        for b in banks:
            if not b.post_number:
                return True
            return self._check_9_pos_postal_num(b.post_number) or \
                   self._check_5_pos_postal_num(b.post_number)


    _constraints = [(_check_postal_num,
                    'Please enter a correct postal number. (01-23456-1 or 12345)',
                    ['post_number'])]

    _sql_constraints = [('bvr_adherent_uniq', 'unique (bvr_adherent_num)',
        'The BVR adherent number must be unique !')]

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
