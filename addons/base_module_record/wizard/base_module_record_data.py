# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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

from osv import osv, fields
import tools
from tools.translate import _

class base_module_data(osv.osv_memory):
    _name = 'base.module.data'
    _description = "Base Module Data"
        
    def default_get(self, cr, uid, fields, context=None):
         mod = self.pool.get('ir.model')
         res = super(base_module_data, self).default_get(cr, uid, fields, context=context)
         
         list = ('ir.ui.view', 'ir.ui.menu', 'ir.model', 'ir.model.fields', 'ir.model.access',\
            'res.partner', 'res.partner.address', 'res.partner.category', 'workflow',\
            'workflow.activity', 'workflow.transition', 'ir.actions.server', 'ir.server.object.lines')
         if 'objects' in fields:
             res.update({'objects': mod.search(cr, uid, [('model', 'in', list)])})
         cr.execute('select max(create_date) from ir_model_data')
         c = (cr.fetchone())[0].split('.')[0]
         c = time.strptime(c, "%Y-%m-%d %H:%M:%S")
         sec = c.tm_sec!=59 and c.tm_sec + 1
         c = (c[0], c[1], c[2], c[3], c[4], sec, c[6], c[7], c[8])
         if 'check_date' in fields:
             res.update({'check_date': time.strftime("%Y-%m-%d %H:%M:%S",c)})
         return res

    _columns = {
        'check_date': fields.datetime('Record from Date', required=True),
        'objects': fields.many2many('ir.model', 'base_module_record_object_rel', 'objects', 'model_id', 'Objects'),
        'filter_cond': fields.selection([('created', 'Created'), ('modified', 'Modified'), ('created_modified', 'Created & Modified')], 'Records only', required=True),
        'info_yaml': fields.boolean('YAML'),
    }
    _defaults = {
        'check_date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'filter_cond': 'created',
    }
    
    def _create_xml(self, cr, uid, data, context=None):
        mod = self.pool.get('ir.module.record')
        res_xml = mod.generate_xml(cr, uid)
        return {'res_text': res_xml }
    
    def _create_yaml(self, cr, uid, data, context=None):
        mod = self.pool.get('ir.module.record')
        res_xml = mod.generate_yaml(cr, uid)
        return { 'res_text': res_xml }    
    
    def record_objects(self, cr, uid, ids, context=None):
        data = self.read(cr, uid, ids, [], context=context)[0]
        check_date = data['check_date']
        filter = data['filter_cond']
        user = (self.pool.get('res.users').browse(cr, uid, uid)).login
        mod = self.pool.get('ir.module.record')
        mod_obj = self.pool.get('ir.model')
        mod.recording_data = []
        for id in data['objects']:
            obj_name=(mod_obj.browse(cr, uid, id)).model
            obj_pool=self.pool.get(obj_name)
            if filter =='created':
                search_condition =[('create_date','>',check_date)]
            elif filter =='modified':
                search_condition =[('write_date','>',check_date)]
            elif filter =='created_modified':
                search_condition =['|',('create_date','>',check_date),('write_date','>',check_date)]
            if '_log_access' in dir(obj_pool):
                  if not (obj_pool._log_access):
                      search_condition=[]
                  if '_auto' in dir(obj_pool):
                      if not obj_pool._auto:
                          continue
            search_ids=obj_pool.search(cr,uid,search_condition)
            for s_id in search_ids:
                 args=(cr.dbname,uid,obj_name,'copy', s_id,{}, context)
                 mod.recording_data.append(('query', args, {}, s_id))
         
        mod_obj = self.pool.get('ir.model.data')
        if len(mod.recording_data):
            if data['info_yaml']:
                res=self._create_yaml(cr, uid, data, context)
                model_data_ids = mod_obj.search(cr, uid, [('model', '=', 'ir.ui.view'), ('name', '=', 'module_create_xml_view')], context=context)
                resource_id = mod_obj.read(cr, uid, model_data_ids, fields=['res_id'], context=context)[0]['res_id']
                return {
                    'name': _('Message'),
                    'context':  {
                        'default_res_text': tools.ustr(res['res_text']),
                        },
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'base.module.record.data',
                    'views': [(resource_id, 'form')],
                    'type': 'ir.actions.act_window',
                    'target': 'new',
                }
            else:
                res=self._create_xml(cr, uid, data, context)
                model_data_ids = mod_obj.search(cr, uid, [('model', '=', 'ir.ui.view'), ('name', '=', 'module_create_xml_view')], context=context)
                resource_id = mod_obj.read(cr, uid, model_data_ids, fields=['res_id'], context=context)[0]['res_id']
                return {
                    'name': _('Message'),
                    'context':  {
                        'default_res_text': tools.ustr(res['res_text']),
                        },
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'base.module.record.data',
                    'views': [(resource_id, 'form')],
                    'type': 'ir.actions.act_window',
                    'target': 'new',
                }
        model_data_ids = mod_obj.search(cr, uid,[('model', '=', 'ir.ui.view'), ('name', '=', 'module_recording_message_view')], context=context)
        resource_id = mod_obj.read(cr, uid, model_data_ids, fields=['res_id'], context=context)[0]['res_id']
        
        return {
            'name': _('Message'),
            'context': context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'base.module.record.objects',
            'views': [(resource_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'new',
        }      
        
base_module_data()

class base_module_record_data(osv.osv_memory):
    _name = 'base.module.record.data'
    _description = "Base Module Record Data"
                
    _columns = {
        'res_text': fields.text('Result'),
    }    
    
base_module_record_data()

#vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: