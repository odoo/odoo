# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

import netsvc
from osv import fields, osv

def _format_iban(string):
    '''
    This function removes all characters from given 'string' that isn't a alpha numeric and converts it to lower case.
    '''
    res = ""
    for char in string:
        if char.isalnum():
            res += char.lower()
    return res

class res_partner_bank(osv.osv):
    _inherit = "res.partner.bank"

    def create(self, cr, uid, vals, context={}):
        #overwrite to format the iban number correctly
        if 'iban' in vals and vals['iban']:
            vals['iban'] = _format_iban(vals['iban'])
        return super(res_partner_bank, self).create(cr, uid, vals, context)

    def write(self, cr, uid, ids, vals, context={}):
        #overwrite to format the iban number correctly
        if 'iban' in vals and vals['iban']:
            vals['iban'] = _format_iban(vals['iban'])
        return super(res_partner_bank, self).write(cr, uid, ids, vals, context)

    def check_iban(self, cr, uid, ids):
        '''
        Check the IBAN number
        '''
        for bank_acc in self.browse(cr, uid, ids):
            if not bank_acc.iban:
                continue
            iban =_format_iban(bank_acc.iban) 
            #the four first digits have to be shifted to the end
            iban = iban[4:] + iban[:4]
            #letters have to be transformed into numbers (a = 10, b = 11, ...)
            iban2 = ""
            for char in iban:
                if char.isalpha():
                    iban2 += str(ord(char)-87)
                else:
                    iban2 += char
            #iban is correct if modulo 97 == 1
            if not int(iban2) % 97 == 1:
                return False
        return True

    def name_get(self, cr, uid, ids, context=None):
        res = []
        to_check_ids = []
        for id in self.browse(cr, uid, ids):
            if id.state=='iban':
                res.append((id.id,id.iban))
            else:
                to_check_ids.append(id.id)
        res += super(res_partner_bank, self).name_get(cr, uid, to_check_ids, context)
        return res

    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
    #overwrite the search method in order to search not only on bank type == basic account number but also on type == iban
        res = super(res_partner_bank,self).search(cr, uid, args, offset, limit, order, context=context, count=count)
        if filter(lambda x:x[0]=='acc_number' ,args):
            #get the value of the search
            iban_value = filter(lambda x:x[0]=='acc_number' ,args)[0][2]
            #get the other arguments of the search
            args1 =  filter(lambda x:x[0]!='acc_number' ,args)
            #add the new criterion
            args1 += [('iban','ilike',iban_value)]
            #append the results to the older search
            res += super(res_partner_bank,self).search(cr, uid, args1, offset, limit,
                order, context=context, count=count)
        return res

    def get_bban_from_iban(self, cr, uid, ids, context=None):
        '''
        This function returns the bank account number computed from the iban account number, thanks to the mapping_list dictionary that contains the rules associated to its country.
        '''
        res = {}
        mapping_list = {
         #TODO add rules for others countries
            'be': lambda x: x[4:],
            'fr': lambda x: x[14:],
            'ch': lambda x: x[9:],
            'gb': lambda x: x[14:],
        }
        for record in self.browse(cr, uid, ids, context):
            if not record.iban:
                res[record.id] = False
                continue
            res[record.id] = False
            for code, function in mapping_list.items():
                if record.iban.lower().startswith(code):
                    res[record.id] = function(record.iban)
                    break
        return res

    _columns = {
        'iban': fields.char('IBAN', size=34, readonly=True, help="International Bank Account Number"),
    }

    _constraints = [(check_iban, "The IBAN number doesn't seem to be correct.", ["iban"])]

res_partner_bank()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

