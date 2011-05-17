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
        'partner': fields.selection([('Customer','Customer'),
                                  ('Client','Client'),
                                  ('Member','Member'),
                                  ('Patient','Patient'),
                                  ('Partner','Partner'),
                                  ('Donor','Donor'),
                                  ('Guest','Guest'),
                                  ('Tenant','Tenant')
                                  ],
                                 'Choose how to call a customer', required=True ),
                                 
        'products' : fields.char('Choose how to call a Product', size=64),
        
    }
    _defaults={
               'partner' :'Partners',
               'products' :'Product'
    }
    
    def execute(self, cr, uid, ids, context=None):
        for o in self.browse(cr, uid, ids, context=context):
            user_obj = self.pool.get('res.users')
            trans_obj = self.pool.get('ir.translation')
            ir_model = self.pool.get('ir.model.fields')
            ir_model_prod_id = ir_model.search(cr,uid, [('field_description','like','Product')])
            ir_model_partner_id = ir_model.search(cr,uid, [('field_description','like','Partner')])
            trans_id = trans_obj.search(cr,uid, [],context=context)
            browse_val = user_obj.browse(cr ,uid ,uid , context=context)
            context_lang = browse_val.context_lang
            # For Partner Translation
            if ir_model_prod_id:
                for p_id in ir_model_partner_id:
                    brw_ir_model = ir_model.browse(cr ,uid ,p_id , context=context)
                    name1 = brw_ir_model.field_description
                    name2 = name1.replace('Partner',o.partner)
                    obj2 = brw_ir_model.model_id.model
                    field = brw_ir_model.name
                    partner_name = obj2 +',' + field
                    already_id = trans_obj.search(cr,uid, [('name','=',partner_name)])
                    if already_id:
                        for un_id in already_id:
                            trans_obj.unlink(cr ,uid, un_id, context=context )
                    created_id = trans_obj.create(cr, uid, {'name': partner_name ,'lang': context_lang, 'type': 'field',  'src': name1, 'value': name2}, context=context)
            # For Product Translation
            if ir_model_prod_id:
                for prd_id in ir_model_prod_id:
                    brw_prod_ir_model = ir_model.browse(cr ,uid ,prd_id , context=context)
                    name_prod1 = brw_prod_ir_model.field_description
                    name_prod2 = name_prod1.replace('Product',o.products)
                    obj_prod = brw_prod_ir_model.model_id.model
                    prod_field = brw_prod_ir_model.name
                    product_name = obj_prod +',' + prod_field
                    already_prod_id = trans_obj.search(cr,uid, [('name','=',product_name)])
                    if already_prod_id:
                        for un_id in already_prod_id:
                            trans_obj.unlink(cr ,uid, un_id, context=context )
                    created_id = trans_obj.create(cr, uid, {'name': product_name ,'lang': context_lang, 'type': 'field',  'src': name_prod1, 'value': name_prod2}, context=context)
            
        return {}
    
specify_product_terminology()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
