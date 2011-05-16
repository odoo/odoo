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
        'partner': fields.selection([('Customers','Customers'),
                                  ('Clients','Clients'),
                                  ('Members','Members'),
                                  ('Patients','Patients'),
                                  ('Partners','Partners'),
                                  ('Donors','Donors'),
                                  ('Guests','Guests'),
                                  ('Tenants','Tenants')
                                  ],
                                 'Choose how to call a customer', required=True ),
                                 
        'products' : fields.char('Choose how to call a Product', size=64),
        
    }
    _defaults={
               'partner' :'Partners',
    }
    
    def execute(self, cr, uid, ids, context=None):
        for o in self.browse(cr, uid, ids, context=context):
            user_obj = self.pool.get('res.users')
            trans_obj = self.pool.get('ir.translation')
            browse_val = user_obj.browse(cr ,uid ,uid , context=context)
            name = browse_val.name
            context_lang = browse_val.context_lang
            name_prt = 'res.partner,name'
            name_prod = 'product.template,name'
            trans_obj.create(cr, uid, {'name': name_prt ,'lang': context_lang, 'type': 'field',  'src': 'Name', 'value': o.partner}, context=context)
            trans_obj.create(cr, uid, {'name': name_prod ,'lang': context_lang, 'type': 'field',  'src': 'Name', 'value': o.products}, context=context)
        return {}
    
specify_product_terminology()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
