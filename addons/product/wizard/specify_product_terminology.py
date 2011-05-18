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
    
    def trnslate_create(self, cr, uid, ids, name, type, src, value,res_id = False, context=None):
        if context is None:
            context = {}
        trans_obj = self.pool.get('ir.translation')
        user_obj = self.pool.get('res.users')
        context_lang = user_obj.browse(cr ,uid ,uid , context=context).context_lang
        if res_id == False :
            res_id = 0
        already_id = trans_obj.search(cr,uid, [('name','=',name),('res_id','=',res_id)])
        if already_id:
            for un_id in already_id:
                trans_obj.unlink(cr ,uid, un_id, context=context )
        create_id = trans_obj.create(cr, uid, {'name': name ,'lang': context_lang, 'type': type,  'src': src, 'value': value , 'res_id':res_id}, context=context)
        return {}
    
    
    def execute(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        for o in self.browse(cr, uid, ids, context=context):
            trans_obj = self.pool.get('ir.translation')
            ir_model = self.pool.get('ir.model.fields')
            ir_menu = self.pool.get('ir.ui.menu')
            ir_model_prod_id = ir_model.search(cr,uid, [('field_description','like','Product')])
            ir_model_partner_id = ir_model.search(cr,uid, [('field_description','like','Partner')])
            ir_menu_product_id = ir_menu.search(cr,uid, [('name','like','Product')])
            ir_menu_partner_id = ir_menu.search(cr,uid, [('name','like','Partner')])
            # For Partner Translation
            if ir_model_prod_id:
                for p_id in ir_model_partner_id:
                    brw_ir_model = ir_model.browse(cr ,uid ,p_id , context=context)
                    name1 = brw_ir_model.field_description
                    name2 = name1.replace('Partner',o.partner)
                    obj2 = brw_ir_model.model_id.model
                    field = brw_ir_model.name
                    partner_name = obj2 +',' + field
                    self.trnslate_create(cr, uid, ids, partner_name, 'field', name1 ,name2 ,context=context )
                    
            if ir_menu_partner_id:
                for m_id in ir_menu_partner_id:
                    brw_partner_menu = ir_menu.browse(cr ,uid ,m_id , context=context)
                    menu_partner_name1 = brw_partner_menu.name
                    menu_partner_name2 = menu_partner_name1.replace('Partner',o.partner)
                    res_id = m_id
                    menu_partnr_name = 'ir.ui.menu' + ',' + 'name'
                    self.trnslate_create(cr, uid, ids, menu_partnr_name, 'model', menu_partner_name1 , menu_partner_name2, res_id ,context=context )
                    
            # For Product Translation
            if ir_model_prod_id:
                for prd_id in ir_model_prod_id:
                    brw_prod_ir_model = ir_model.browse(cr ,uid ,prd_id , context=context)
                    name_prod1 = brw_prod_ir_model.field_description
                    name_prod2 = name_prod1.replace('Product',o.products)
                    obj_prod = brw_prod_ir_model.model_id.model
                    prod_field = brw_prod_ir_model.name
                    product_name = obj_prod +',' + prod_field
                    self.trnslate_create(cr, uid, ids, product_name, 'field', name_prod1 ,name_prod2 ,context=context )
                    
            if ir_menu_product_id:
                for m_id in ir_menu_product_id:
                    brw_menu = ir_menu.browse(cr ,uid ,m_id , context=context)
                    menu_name1 = brw_menu.name
                    menu_name2 = menu_name1.replace('Product',o.products)
                    res_id = m_id
                    menu_name = 'ir.ui.menu' + ',' + 'name'
                    self.trnslate_create(cr, uid, ids, menu_name, 'model', menu_name1 , menu_name2, res_id ,context=context )
                    
        return {}
    
specify_product_terminology()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
