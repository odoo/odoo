# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011
#    Associazione OpenERP Italia (<http://www.openerp-italia.org>)
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
import decimal_precision as dp
from decimal import *

class account_tax(osv.osv):

    _inherit = 'account.tax'

    def compute_all(self, cr, uid, taxes, price_unit, quantity, address_id=None, product=None, partner=None):
        res = super(account_tax, self).compute_all(cr, uid, taxes, price_unit, quantity, address_id, product, partner)
        
        precision = self.pool.get('decimal.precision').precision_get(cr, uid, 'Account')
        tax_list = res['taxes']
        totalex = res['total']
        if len(tax_list) == 2:
            for tax in tax_list:
                if tax.get('balance',False): # Calcolo di imponibili e imposte per l'IVA parzialmente detraibile
                    deductible_base = totalex
                    ind_tax = tax_list[abs(tax_list.index(tax)-1)]
                    ind_tax_obj = self.browse(cr, uid, ind_tax['id'])
                    ded_tax_obj = self.browse(cr, uid, tax['id'])
                    base_ind = float(Decimal(str(totalex * ind_tax_obj.amount)).quantize(Decimal('1.'+precision*'0'), rounding=ROUND_HALF_UP))
                    base_ded = float(Decimal(str(totalex - base_ind)).quantize(Decimal('1.'+precision*'0'), rounding=ROUND_HALF_UP))
                    tax_total = float(Decimal(str(tax['balance'])).quantize(Decimal('1.'+precision*'0'), rounding=ROUND_HALF_UP))
                    tax_ind = float(Decimal(str(tax_total * ind_tax_obj.amount)).quantize(Decimal('1.'+precision*'0'), rounding=ROUND_HALF_UP))
                    tax_ded = tax_total - tax_ind
                    ind_tax['price_unit']  = base_ind
                    tax['price_unit'] = base_ded
                    ind_tax['amount']  = tax_ind
                    tax['amount'] = tax_ded

        return res

account_tax()
