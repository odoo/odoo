# -*- encoding: utf-8 -*-
#  bank.py
#  l10n_ch
#
#  Created by Nicolas Bessi based on Credric Krier contribution
#
#  Copyright (c) 2010 CamptoCamp. All rights reserved.
##############################################################################
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

from osv import fields, osv


class Bank(osv.osv):
    """Inherit res.bank class in order to add swiss specific field"""
    _inherit = 'res.bank'
    _columns = {
        ### Swiss unik bank identifier also use in IBAN number
        'clearing': fields.char('Clearing number', size=64),
        ### City of the bank
        'city': fields.char('City', size=128, select=1),
    }

Bank()


class ResPartnerBank(osv.osv):
    """Override of res.partner.bank"""
    
    _inherit = "res.partner.bank"
    _columns = {
        ## Account number
        'acc_number': fields.char(
                                    'Account Number', 
                                    size=64, 
                                    required=False,
                                    help='Bank account number'
                                    ),
        ## Account name
        'name': fields.char(
                                'Description', 
                                size=128, 
                                required=True,
                            ),
        ## Post account code to be redesing
        'post_number': fields.char(
                                    'Post number', 
                                    size=64,
                                    help='CCP, postal account number used for '+
                                    'postal payment format xx-xxxx-x'
                                    ),
        ## Post account code to be redesing
        'bvr_number': fields.char(
                                    'BVR account number', 
                                    size=11,
                                    help='Postal account number of the '+ 
                                    'financial establishment.'+
                                    'Used foe BV bank payment '+
                                    'format xx-xxxxx-x'
                                    
                                ),
        ## Post financne affiliation number
        'bvr_adherent_num': fields.char(
                                        'BVR adherent number', 
                                         size=11,
                                         help='PostFinance affiliation BVR number '+
                                         'of your financial establishement'+
                                         'used for BVR/ESR printing'
                                        ),
        ## DTA code used by Mammuth
        'dta_code': fields.char(
                                'DTA code', 
                                size=5,
                                help='Code used by transfer system for '+
                                'identify the bank. Ex Mammuth'
                                ),
        ### Will print the Bank name on BVR/ESR
        'printbank' : fields.boolean(
                                'Print Bank on BVR',
                                help='will print bank name on the ESR/BVR'
                                    ),
        ### Will print the Bank account on BVR/ESR
        'printaccount' : fields.boolean(
                                        'Print Account Number on BVR',
                                        help='will print bank account'+
                                        'name on the ESR/BVR'
                                        ),
    }
        
    def name_get(self, cursor, uid, ids, context=None):
        """Override of the name get function of the bank 
        in order to have the partner link to the bank"""
        if not len(ids):
            return []
        bank_type_obj = self.pool.get('res.partner.bank.type')

        type_ids = bank_type_obj.search(cursor, uid, [])
        bank_type_names = {}
        for bank_type in bank_type_obj.browse(cursor, uid, type_ids,
                context=context):
            bank_type_names[bank_type.code] = bank_type.name
        res = []
        for bank in self.read(cursor, uid, ids, ['name', 'state'], context):
            res.append((bank['id'], bank['name']+
                ' : '+bank_type_names[bank['state']]))
        return res
    
    _sql_constraints = [
        ('bvr_adherent_uniq', 'unique (bvr_adherent_num)', 
            'The BVR adherent number must be unique !')
    ]
ResPartnerBank()