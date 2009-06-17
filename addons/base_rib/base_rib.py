# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import string
import unicodedata

import netsvc
from osv import fields, osv

# Add fields and behavior for French RIB
class res_partner_bank(osv.osv):
    _inherit = "res.partner.bank"

    def _check_key(self, cr, uid, ids):
        '''
        Check the RIB key
        '''
        for bank_acc in self.browse(cr, uid, ids):
            # ignore the accounts of type other than rib
            if bank_acc.state !='rib':
                continue
            
            # Fail if the needed values are empty of too short 
            if (not bank_acc.bank or not bank_acc.bank.code or len(bank_acc.bank.code) != 5
            or not bank_acc.office or len(bank_acc.office) != 5
            or not bank_acc.acc_number or len(bank_acc.acc_number) != 11
            or not bank_acc.key or len(bank_acc.key) != 2):
                return False
            
            # get the rib data (without the key)
            rib = "%s%s%s" % (bank_acc.bank.code, bank_acc.office, bank_acc.acc_number)
            # translate letters into numbers according to a specific table (notice how s -> 2)
            # Note: maketrans and translate work best with latin1 - that should not be a problem for RIB data
            rib = rib.lower().encode('latin-1').translate(string.maketrans(u'abcdefghijklmnopqrstuvwxyz', u'12345678912345678923456789'))
            
            # compute the key
            key = 97 - (100 * int(rib)) % 97
            
            if int(bank_acc.key) != key:
                return False
        return True

    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
    #overwrite the search method in order to search not only on bank type == basic account number but also on type == rib
        res = super(res_partner_bank, self).search(cr, uid, args, offset, limit, order, context=context, count=count)
        if filter(lambda x:x[0] == 'acc_number' , args):
            #get the value of the search
            rib_value = filter(lambda x:x[0] == 'acc_number' , args)[0][2]
            #get the other arguments of the search
            args1 = filter(lambda x:x[0] != 'acc_number' , args)
            #add the new criterion
            args1 += [('rib', 'ilike', rib_value)]
            #append the results to the older search
            res += super(res_partner_bank, self).search(cr, uid, args1, offset, limit,
                order, context=context, count=count)
        return res

    _columns = {
        'office': fields.char('Office Code', size=5, readonly=True, help="Office Code"),
        'key': fields.char('Key', size=2, readonly=True, help="The key is a number allowing to check the correctness of the other codes."),
    }
    
    _constraints = [(_check_key, "The RIB key does not correspond to the other codes.", ["key"])]
    
res_partner_bank()

# overload the name_search method on banks to make it easier to enter RIB data
class res_bank(osv.osv):
    _inherit = 'res.bank'

    # allow a search by code
    def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=80):
        if not args:
            args = []
        if context is None:
            context = {}
        ids = []
        if name:
            ids = self.search(cr, user, [('name', operator, name)] + args, limit=limit, context=context)
        if not ids:
            ids = self.search(cr, user, [('code', operator, name)] + args, limit=limit, context=context)
        return self.name_get(cr, user, ids, context)

    # show the code before the name
    def name_get(self, cr, uid, ids, context=None):
        result = []
        for bank in self.browse(cr, uid, ids, context):
            result.append((bank.id, (bank.code and (bank.code + ' - ') or '') + bank.name))
        return result

res_bank()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

