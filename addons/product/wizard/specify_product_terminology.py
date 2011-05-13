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
        
        partner_list = []
        product_list = []
        #For Partner selection 
        if partner == 'partners':
            partner_list  =[ {'new_name': 'partner','old_name':'partner'},{'new_name': 'Partner','old_name':'Partner'},{'new_name': 'partners','old_name':'partners'},{'new_name': 'Partners','old_name':'Partners'}]
            
        if partner == 'customers':
            partner_list  =[ {'new_name': 'customer','old_name':'partner'},{'new_name': 'Customer','old_name':'Partner'},{'new_name': 'customers','old_name':'customers'},{'new_name': 'Customers','old_name':'Customers'}]
        
        if partner == 'clients':
            partner_list  =[ {'new_name': 'client','old_name':'partner'},{'new_name': 'Client','old_name':'Partner'},{'new_name': 'clients','old_name':'partners'},{'new_name': 'Clients','old_name':'Partners'}]

        if partner == 'members':
            partner_list  =[ {'new_name': 'member','old_name':'partner'},{'new_name': 'Member','old_name':'Partner'},{'new_name': 'members','old_name':'partners'},{'new_name': 'Members','old_name':'Partners'}]

        if partner == 'patients':
            partner_list  =[ {'new_name': 'patient','old_name':'partner'},{'new_name': 'Patient','old_name':'Partner'},{'new_name': 'patients','old_name':'partners'},{'new_name': 'Patients','old_name':'Partners'}]

        if partner == 'donors':
            partner_list  =[ {'new_name': 'donor','old_name':'partner'},{'new_name': 'Donor','old_name':'Partner'},{'new_name': 'donors','old_name':'partners'},{'new_name': 'Donors','old_name':'Partners'}]

        if partner == 'guests':
            partner_list  =[ {'new_name': 'guest','old_name':'partner'},{'new_name': 'Guest','old_name':'Partner'},{'new_name': 'guests','old_name':'partners'},{'new_name': 'Guests','old_name':'Partners'}]

        if partner == 'tenants':
            partner_list  =[ {'new_name': 'tenant','old_name':'partner'},{'new_name': 'Tenant','old_name':'Partner'},{'new_name': 'tenants','old_name':'partners'},{'new_name': 'Tenants','old_name':'Partners'}]
        
        # For Product selection
        if products == 'products':
            product_list  =[ {'new_name': 'product','old_name':'product'},{'new_name': 'Product','old_name':'Product'},{'new_name': 'products','old_name':'products'},{'new_name': 'Products','old_name':'Products'}]

        if products == 'contracts':
            product_list  =[ {'new_name': 'contract','old_name':'product'},{'new_name': 'Contract','old_name':'Product'},{'new_name': 'contracts','old_name':'products'},{'new_name': 'Contracts','old_name':'Products'}]

        if products == 'goods':
            product_list  =[ {'new_name': 'goods','old_name':'product'},{'new_name': 'Goods','old_name':'Product'},{'new_name': 'goods','old_name':'products'},{'new_name': 'Goods','old_name':'Products'}]

        if products == 'services':
            product_list  =[ {'new_name': 'service','old_name':'product'},{'new_name': 'Service','old_name':'Product'},{'new_name': 'services','old_name':'products'},{'new_name': 'Services','old_name':'Products'}]

        if products == 'membership':
            product_list  =[ {'new_name': 'membership','old_name':'product'},{'new_name': 'Membership','old_name':'Product'},{'new_name': 'memberships','old_name':'products'},{'new_name': 'Memberships','old_name':'Products'}]

        if products == 'artwork':
            product_list  =[ {'new_name': 'artwork','old_name':'product'},{'new_name': 'Artwork','old_name':'Product'},{'new_name': 'artworks','old_name':'products'},{'new_name': 'Artworks','old_name':'Products'}]
       
        term_list = partner_list + product_list
        
        return {'value' : {'terminolgy_ids': term_list}}

    
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
