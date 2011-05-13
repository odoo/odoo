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
from osv import fields, osv
import pooler
import pytz


class specify_product_terminology(osv.osv_memory):
    _name = 'specify.product.terminology'
    _inherit = 'res.config'
    _columns = {
        'partner': fields.selection([('customers','Customers'),
                                  ('clients','Clients'),
                                  ('members','Members'),
                                  ('patients','Patients'),
                                  ('partners','Partners'),
                                  ('donors','Donors'),
                                  ('guests','Guests'),
                                  ('tenants','Tenants')
                                  ],
                                 'Choose how to call a Partner', required=True ),
        
        'products': fields.selection([('products','Products'),
                                  ('contracts','Contracts'),
                                  ('goods','Goods'),
                                  ('services','Services'),
                                  ('membership','Membership'),
                                  ('artwork','Artwork')
                                  ],
                                 'Choose how to call a Product', required=True ),
        
        'terminolgy_ids':fields.one2many('product.treminolg.old.new.wizard', 'wizard_id', 'Wizard Reference'),
                                 
    }
    _defaults={
               'partner' :'partners',
               'products' :'products'
    }
    
    def onchange_partner_product_term(self, cr, uid, ids, partner,products,context=None):
        return {'value' : {'terminolgy_ids': [{'new_name': partner,'old_name':'Partners'},{'new_name': products,'old_name':'Products'}]}}
    
specify_product_terminology()

class product_treminolg_old_new_wizard(osv.osv_memory):
    _name = "product.treminolg.old.new.wizard"
    _columns = {
         'wizard_id': fields.many2one('specify.product.terminology','Terminology', required=True),
         'old_name': fields.char('Old Name', size=64, required=True, translate=True),
         'new_name': fields.char('New Name', size=64, required=True, translate=True),
         
     }
    
product_treminolg_old_new_wizard()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
