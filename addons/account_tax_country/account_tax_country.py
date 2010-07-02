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

import time
import netsvc
from osv import fields, osv

from tools.misc import currency
from tools.translate import _
class account_tax(osv.osv):
    _inherit='account.tax'
    _columns = {
                'country_id':fields.many2many('res.country','country_invoice_line_tax','invoice_line_id','tax_id',string='Country'),
                }
account_tax()    
class account_invoice(osv.osv):
    _inherit='account.invoice'

    def _checkreset_taxes(self, cr, uid, ids, context=None):
        
        for invoice in self.browse(cr,uid,ids):
           flag=False
           country_id = invoice.address_invoice_id.country_id.id
           for i in invoice.invoice_line:
               tax_ids=i.invoice_line_tax_id
               for tax in tax_ids:
                   for country in  tax.country_id:
                       if country_id!=country.id:
                        flag=True
               if flag:         
                   raise osv.except_osv(_('Error!'), _('Find a valid Tax of country  !'))
        return True       
    _constraints = [
        (_checkreset_taxes, 'Unable to find a valid country in Tax', ['invoice_line'])
    ]
          
      
account_invoice()    
