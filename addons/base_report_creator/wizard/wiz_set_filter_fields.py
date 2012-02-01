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

from osv import fields, osv
import tools
from tools.translate import _

relation_type=['one2many','many2one','many2many']
char_type = ['char','text','selection']
date_type = ['date','datetime']
int_type = ['float','integer']
remaining_type = ['binary','boolean','reference']
mapping_fields = {'$': 'End With', 'not in': 'Not Contains', '<>': 'Not Equals', 'is': 'Is Empty', 'in': 'Contains', '>': 'Bigger', '=': 'Equals', '<': 'Smaller', 'is not': 'Is Not Empty', '^': 'Start With'}

class set_filter_fields(osv.osv_memory):

    _name = "set.filter.fields"
    _description = "Set Filter Fields"
    
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if context is None:
            context = {}
        res = super(set_filter_fields, self).fields_view_get(cr, uid, view_id, view_type, context=context, toolbar=toolbar, submenu=submenu)
        if context.get('active_model') == 'base_report_creator.report':
            active_id = context.get('active_id')
            active_model = self.pool.get(context.get('active_model'))
            this_data = active_model.read(cr, uid, active_id, context=context)
            res['fields']['field_id']['domain'] = [('model_id','in',this_data.get('model_ids')),('ttype','<>','many2many'),('ttype','<>','one2many')]
        return res

    def open_form(self, cr, uid, ids, context=None):
        data = self.read(cr, uid, ids, [], context=context)[0]
        obj_model = self.pool.get('ir.model.data')
        model_data_ids = obj_model.search(cr,uid,[('model','=','ir.ui.view'),('name','=','view_wiz_set_filter_value_view')])
        resource_id = obj_model.read(cr, uid, model_data_ids, fields=['res_id'], context=context)[0]['res_id']
        field_type = self.browse(cr, uid, ids, context=context)[0].field_id.ttype
        operator = (field_type=='many2one') and 'in' or '='
        return {
             'name': _('Set Filter Values'),
             'context': {
                 'field_id':data['field_id'][0],
                 'default_field_id': data['field_id'],
                 'default_operator': operator,
                 },
             'view_type': 'form',
             'view_mode': 'form',
             'res_model': 'set.filter.value',
             'views': [(resource_id, 'form')],
             'type': 'ir.actions.act_window',
             'target': 'new',
             }

    _columns = {
        'field_id': fields.many2one('ir.model.fields', "Filter Field", required=True),
   }

set_filter_fields()

class set_filter_value(osv.osv_memory):

    _name = "set.filter.value"
    _description = "Set Filter Values"
    
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if context is None:
            context = {}
        obj_ir_model_fields = self.pool.get('ir.model.fields')
        res = super(set_filter_value, self).fields_view_get(cr, uid, view_id, view_type, context=context, toolbar=toolbar, submenu=submenu)
        operator_select = []
        field  = {}
        if context.get('field_id', False):
            field_data = obj_ir_model_fields.read(cr,uid,[context['field_id']], context=context)[0]
            fields_dict = self.pool.get(field_data.get('model')).fields_get(cr,uid,fields=[field_data.get('name')])
            value_field = res['fields']['value']
            field_type = field_data.get('ttype',False)
            for k,v in value_field.items():
                if k in ('size','relation','type'):
                    del value_field[k]
                    
            if field_type in ('one2many','many2many','many2one'):
                value_field['type'] = 'many2many'
                value_field['relation'] = field_data.get('relation')
                for key, value in res['fields'].items():
                    if key == 'value':
                        field[key] = fields.many2many(field_data.get('relation'),'relation_table','first_id','second_id', value['string'])
                        self._columns.update(field)
            
            else:
                value_field['type'] = field_type
                for key, value in res['fields'].items():
                    if key == 'value':
                        field[key] = fields.char(value['string'],size=256)
                        self._columns.update(field)
                if field_type == 'selection':
                    selection_data = self.pool.get(field_data['model']).fields_get(cr,uid,[field_data['name']])
                    print "selection_data", selection_data
                    value_field['selection'] = selection_data.get(field_data['name']).get('selection')
                    for key, value in res['fields'].items():
                        if key == 'value':
                            field[key] = fields.selection(value_field['selection'], value['string'])
                            self._columns.update(field)
                             
            for field in res['fields']:
                if field == 'operator':
                    if field_type == 'many2one':
                        operator_select = [('in', 'Equals'), ('in', 'Contains'),('not in', 'Not Contains'), ('is','Is Empty'), ('is not','Is Not Empty')]
                    elif field_type in ('char', 'text'):
                        operator_select = [('=','Equals'),('in','Contains'),('<>','Not Equals'),('not in','Not Contains'),('^','Start With'),('$','End With'),('is','Is Empty'),('is not','Is Not Empty')]
                    elif field_type in ('date', 'datetime', 'integer', 'float'):                    
                        operator_select = [('=','Equals'),('<>','Not Equals'), ('is','Is Empty'),('is not','Is Not Empty'), ('<','Smaller'), ('>','Bigger')]
                    elif field_type in ('boolean', 'selection'):
                        operator_select = [('=','Equals'),('<>','Not Equals')]
                    res['fields'][field]['selection'] = operator_select
              
        return res

    _columns = {
        'field_id': fields.many2one('ir.model.fields', "Filter Name", required=True),
        #'field_id': fields.many2one('ir.model.fields', "Filter Name", required=True, readonly=True), To do fix
        'operator': fields.selection(selection=[], string='Operator'),
        'value': fields.char('Values', size=256),
        'condition' : fields.selection([('and','AND'),('or','OR')], 'Condition'),
    }

    _defaults = {
         'condition': 'and',
     }
    
    def set_field_operator(self, field_name, field_type, search_operator, search_value):
        field_search = [field_name,search_operator,search_value]
        if search_operator == '=':
            if field_type=='many2one':
                field_search[1]='in'
                field_search[2] = "("+','.join([str(x) for x in search_value])+")"
            elif field_type in char_type or field_type in date_type:
                field_search[2] = field_search[2] and "'"+field_search[2]+"'" or False
        elif search_operator == '<>':
            if field_type=='many2one':
                field_search[1]='not in'
                field_search[2] = "("+','.join([str(x) for x in search_value])+")"
            elif field_type in char_type or field_type in date_type:
                field_search[2] = "'"+field_search[2]+"'"
        elif search_operator == 'in':
            if field_type=='many2one':
                field_search[2] = "("+','.join([str(x) for x in search_value])+")"
            else:
                field_search[1] = 'ilike'
                field_search[2] = "'%%"+str(search_value)+"%%'"
        elif search_operator == 'not in':
            if field_type=='many2one':
                field_search[2] = "("+','.join([str(x) for x in search_value])+")"
            else:
                field_search[1] = 'not ilike'
                field_search[2] = "'%%"+str(search_value)+"%%'"
        elif search_operator == '^':
            if field_type in char_type:
                field_search[1]='~'
                field_search[2]="'"+str(search_operator)+str(search_value)+"'"
            else:
                return False
        elif search_operator == '$':
            if field_type in char_type:
                field_search[1]='~'
                field_search[2]="'"+search_value+search_operator+"'"
            else:
                return False
            #end if field_type in char_type:
        elif search_operator in ('is','is not'):
            field_search[2] = 'null'
        elif search_operator in ('<','>'):
            if field_type in date_type:
                field_search[2] = "'"+field_search[2]+"'"
            elif field_type not in int_type:
                return False
        return field_search
    
    def set_filter_value(self, cr, uid, ids, context=None):
        obj_ir_model_fields = self.pool.get('ir.model.fields')
        obj_ir_model = self.pool.get('ir.model')
        form_data = self.read(cr, uid, ids, [], context=context)[0]
        value_data = form_data.get('value',False)
        field_type = self.browse(cr, uid, ids, context=context)[0].field_id.ttype
        field_data = obj_ir_model_fields.read(cr,uid,[form_data.get('field_id')[0]],fields=['ttype','relation','model_id','name', 'field_description'],context=context)[0]
        model_name = obj_ir_model.browse(cr, uid, field_data['model_id'][0], context=context).model
        model_pool = self.pool.get(model_name)
        table_name = model_pool._table
        model_name = model_pool._description
        if field_type:
            if field_type == 'boolean':
                if value_data == 1:
                    value_data = 'true'
                else:
                    value_data = 'false'
    
            if field_type in ['float','integer']:
                value_data =  value_data or 0
            if field_type == 'many2many' and value_data and len(value_data):
                fields_list = self.set_field_operator(table_name+"."+field_data['name'],field_data['ttype'],form_data['operator'],value_data[0][2])
            else:
                fields_list = self.set_field_operator(table_name+"."+field_data['name'],field_data['ttype'],form_data['operator'],value_data)
            if fields_list:
                create_dict = {
                               'name':model_name + "/" +field_data['field_description'] +" "+ mapping_fields[form_data['operator']] + " " + tools.ustr(fields_list[2]) + " ",
                               'expression':' '.join(map(tools.ustr,fields_list)),
                               'report_id': context.get('active_id',False),
                               'condition' : form_data['condition']
                               }
                self.pool.get('base_report_creator.report.filter').create(cr, uid, create_dict, context)
        return {'type': 'ir.actions.act_window_close'}

set_filter_value()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: