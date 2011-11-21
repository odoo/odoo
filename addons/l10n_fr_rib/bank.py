# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011 OpenERP SA (<http://openerp.com>).
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

import string
import unicodedata

import netsvc
from osv import fields, osv
from tools.translate import _

class res_partner_bank(osv.osv):
    """Add fields and behavior for French RIB"""
    _inherit = "res.partner.bank"

    def _check_key(self, cr, uid, ids):
        print """Check the RIB key"""
        for bank_acc in self.browse(cr, uid, ids):
            # Ignore the accounts of type other than rib
            if bank_acc.state !='rib':
                continue
            # Fail if the needed values are empty of too short 
            if (not bank_acc.bank_code
            or len(bank_acc.bank_code) != 5
            or not bank_acc.office or len(bank_acc.office) != 5
            or not bank_acc.acc_number or len(bank_acc.acc_number) != 11
            or not bank_acc.key or len(bank_acc.key) != 2):
                return False
            
            # Get the rib data (without the key)
            rib = "%s%s%s" % (bank_acc.bank_code, bank_acc.office,
                              bank_acc.acc_number)
            print rib
            # Translate letters into numbers according to a specific table
            #    (notice how s -> 2)
            # Note: maketrans and translate work best with latin1 - that
            #    should not be a problem for RIB data
            # XXX use dict((ord(a), b) for a, b in zip(intab, outtab)) 
            #    and translate()
            rib = rib.lower().encode('latin-1').translate(
                string.maketrans(u'abcdefghijklmnopqrstuvwxyz',
                                 u'12345678912345678923456789'))
            print rib
            # compute the key
            key = 97 - (100 * int(rib)) % 97
            print int(bank_acc.key), key
            if int(bank_acc.key) != key:
                return False
        return True

    def search(self, cr, uid, args, offset=0, limit=None, order=None,
               context=None, count=False):
        """Search on type == rib"""
        res = super(res_partner_bank, self).search(cr, uid, args, offset,
           limit=limit, order=order, context=context, count=count)
        if filter(lambda x:x[0] == 'acc_number' , args):
            #get the value of the search
            rib_value = filter(lambda x:x[0] == 'acc_number' , args)[0][2]
            #get the other arguments of the search
            args1 = filter(lambda x:x[0] != 'acc_number' , args)
            #add the new criterion
            args1 += [('rib', 'ilike', rib_value)]
            #append the results to the older search
            res += super(res_partner_bank, self).search(cr, uid, args1, offset,
                limit, order, context=context, count=count)
        return res

    def onchange_bank_id(self, cr, uid, ids, bank_id, context=None):
        """Change the bank code"""
        result = super(res_partner_bank, self).onchange_bank_id(cr, uid, ids, bank_id,
                                                        context=context)
        if bank_id:
            bank = self.pool.get('res.bank').browse(cr, uid, bank_id, 
                                                    context=context)
            result['bank_code'] = bank.code
        return {'value': result}

    _columns = {
        'bank_code': fields.char('Bank Code', size=64, readonly=True,),
        'office': fields.char('Office Code', size=5, readonly=True,),
        'key': fields.char('Key', size=2, readonly=True,
                           help="The key is a number allowing to check the "
                                "correctness of the other codes."),
    }
    
    def _construct_constraint_msg(self, cr, uid, ids, context=None):
        """Quote the data in the warning message"""
        if self._check_key(cr, uid, ids):
            return
        # Only process the first id
        if type(ids) not in (int, long):
            id = ids[0]
        rib = self.browse(cr, uid, id, context=context)
        if rib:
            return (_("\nThe RIB key %s does not correspond to the other "
                        "codes: %s %s %s.") %
                        (rib.key, 
                        rib.bank_code, 
                        rib.office,
                        rib.acc_number) )

    _constraints = [(_check_key,
                     _construct_constraint_msg,
                     ["key"])]
    
res_partner_bank()

class res_bank(osv.osv):
    """Add the bank code to make it easier to enter RIB data"""
    _inherit = 'res.bank'

    def name_search(self, cr, user, name, args=None, operator='ilike',
                    context=None, limit=80):
        """Search by bank code"""
        if args is None:
            args = []
        ids = []
        if name:
            ids = self.search(cr, user, [('name', operator, name)] + args,
                              limit=limit, context=context)
        if not ids:
            ids = self.search(cr, user, [('code', operator, name)] + args,
                              limit=limit, context=context)
        return self.name_get(cr, user, ids, context)
        
    _columns = {
        'rib_code': fields.char('RIB Bank Code', size=64),
    }
res_bank()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

