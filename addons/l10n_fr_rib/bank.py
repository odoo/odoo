# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011 Numérigraphe SARL.
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

from openerp.osv import fields, osv
from openerp.tools.translate import _

class res_partner_bank(osv.osv):
    """Add fields and behavior for French RIB"""
    _inherit = "res.partner.bank"

    def _check_key(self, cr, uid, ids):
        """Check the RIB key"""
        for bank_acc in self.browse(cr, uid, ids):
            # Ignore the accounts of type other than rib
            if bank_acc.state != 'rib':
                continue
            # Fail if the needed values are empty of too short 
            if (not bank_acc.bank_code
            or len(bank_acc.bank_code) != 5
            or not bank_acc.office or len(bank_acc.office) != 5
            or not bank_acc.rib_acc_number or len(bank_acc.rib_acc_number) != 11
            or not bank_acc.key or len(bank_acc.key) != 2):
                return False
            # Get the rib data (without the key)
            rib = "%s%s%s" % (bank_acc.bank_code, bank_acc.office, bank_acc.rib_acc_number)
            # Translate letters into numbers according to a specific table
            #    (notice how s -> 2)
            table = dict((ord(a), b) for a, b in zip(
                u'abcdefghijklmnopqrstuvwxyz', u'12345678912345678923456789'))
            rib = rib.lower().translate(table)
            # compute the key	
            key = 97 - (100 * int(rib)) % 97
            if int(bank_acc.key) != key:
                raise osv.except_osv(_('Error!'),
                    _("The RIB key %s does not correspond to the other codes: %s %s %s.") % \
                        (bank_acc.key, bank_acc.bank_code, bank_acc.office, bank_acc.rib_acc_number) )
            if bank_acc.acc_number:
                if not self.is_iban_valid(cr, uid, bank_acc.acc_number):
                    raise osv.except_osv(_('Error!'), _("The IBAN %s is not valid.") % bank_acc.acc_number)
        return True

    def onchange_bank_id(self, cr, uid, ids, bank_id, context=None):
        """Change the bank code"""
        result = super(res_partner_bank, self).onchange_bank_id(cr, uid, ids, bank_id,
                                                        context=context)
        if bank_id:
            value = result.setdefault('value', {})
            bank = self.pool.get('res.bank').browse(cr, uid, bank_id, 
                                                    context=context)
            value['bank_code'] = bank.rib_code
        return result

    _columns = {
        'acc_number': fields.char('Account Number', size=64, required=False),
        'rib_acc_number': fields.char('RIB account number', size=11, readonly=True,),
        'bank_code': fields.char('Bank Code', size=64, readonly=True,),
        'office': fields.char('Office Code', size=5, readonly=True,),
        'key': fields.char('Key', size=2, readonly=True,
                           help="The key is a number allowing to check the "
                                "correctness of the other codes."),
    }

    _constraints = [(_check_key, 'The RIB and/or IBAN is not valid', ['rib_acc_number', 'bank_code', 'office', 'key'])]


class res_bank(osv.osv):
    """Add the bank code to make it easier to enter RIB data"""
    _inherit = 'res.bank'

    def name_search(self, cr, user, name, args=None, operator='ilike',
                    context=None, limit=80):
        """Search by bank code in addition to the standard search"""
        # Get the standard results
        results = super(res_bank, self).name_search(cr, user,
             name, args=args ,operator=operator, context=context, limit=limit)
        # Get additional results using the RIB code
        ids = self.search(cr, user, [('rib_code', operator, name)],
                              limit=limit, context=context)
        # Merge the results
        results = list(set(results + self.name_get(cr, user, ids, context)))
        return results
        
    _columns = {
        'rib_code': fields.char('RIB Bank Code'),
    }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

