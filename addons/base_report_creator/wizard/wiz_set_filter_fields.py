# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import wizard
import netsvc
import pooler

relation_type=['one2many','many2one','many2many']
char_type = ['char','text','selection']
date_type = ['date','datetime']
int_type = ['float','integer']
remaining_type = ['binary','boolean','reference']


select_field_form = """<?xml version="1.0"?>
<form string="Select Field to filter">
    <field name="field_id" nolabel="1">
    </field>
</form>
"""
select_field_fields = {
                       "field_id":{'string':'Filter Field','type':'many2one', 'relation':'ir.model.fields','required':True}
                       }
set_value_form = """<?xml version="1.0"?>
<form string="Set Filter Values">
    <separator colspan="4" string="Filter Values" />
    <field name="field_id" />
    <field name="operator" />
    <field name="value" colspan="4"/>
    <field name="condition" />
</form>
"""

mapping_fields = {'$': 'End With', 'not in': 'Not Contains', '<>': 'Not Equals', 'is': 'Is Empty', 'in': 'Contains', '>': 'Bigger', '=': 'Equals', '<': 'Smaller', 'is not': 'Is Not Empty', '^': 'Start With'}

set_value_fields = {
                    'field_id':{'type':'many2one', 'relation':'ir.model.fields','string':'Field Name','required':True,'readonly':True},
                    'operator':{'type':'selection','selection':[],'string':'Operator'},
                    'value':{'type':'char','string':'Values','size':256},
                    'condition' : {'type':'selection','string':'Condition', 'selection':[('and','AND'),('or','OR')]}
                }
def _set_field_domain(self,cr,uid,data,context):
    this_model = data.get('model')
    this_pooler = pooler.get_pool(cr.dbname).get(this_model)
    this_data = this_pooler.read(cr,uid,data.get('ids'),['model_ids'],context)[0]
    select_field_fields['field_id']['domain'] = [('model_id','in',this_data.get('model_ids')),('ttype','<>','many2many'),('ttype','<>','one2many')] 
    return {'field_id':False}

def set_field_operator(self,field_name,field_type,search_operator,search_value):
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
                field_search[2] = "'%"+str(search_value)+"%'"
        elif search_operator == 'not in':
            if field_type=='many2one':
                field_search[2] = "("+','.join([str(x) for x in search_value])+")"
            else:
                field_search[1] = 'not ilike'
                field_search[2] = "'%"+str(search_value)+"%'"
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
def _set_filter_value(self, cr, uid, data, context):
    form_data = data['form']
    value_data = form_data.get('value',False)
    value_field = set_value_fields.get('value')
    field_type = value_field.get('type',False)
    field_data = pooler.get_pool(cr.dbname).get('ir.model.fields').read(cr,uid,[form_data.get('field_id')],fields=['ttype','relation','model_id','name','field_description'])[0]
    model_name = pooler.get_pool(cr.dbname).get('ir.model').browse(cr, uid, field_data['model_id'][0]).model
    model_pool = pooler.get_pool(cr.dbname).get(model_name)
    table_name = model_pool._table
    model_name = model_pool._description
    
    if field_type:
        if field_type == 'boolean':
            if value_data == 1:
                value_data = 'true'
            else:
                value_data = 'false'
        if field_type == 'many2many' and value_data and len(value_data):
            fields_list = set_field_operator(self,table_name+"."+field_data['name'],field_data['ttype'],form_data['operator'],value_data[0][2])
        else:
            fields_list = set_field_operator(self,table_name+"."+field_data['name'],field_data['ttype'],form_data['operator'],value_data)
        if fields_list:
            create_dict = {
                           'name':model_name + "/" +field_data['field_description'] +" "+ mapping_fields[form_data['operator']] + " " + str(fields_list[2]) + " ",
                           'expression':' '.join(fields_list),
                           'report_id':data['id'],
                           'condition' : form_data['condition']
                           }
            pooler.get_pool(cr.dbname).get('base_report_creator.report.filter').create(cr,uid,create_dict)
        #end if field_type == 'many2many' and value_data and len(value_data):
#       pooler.get_pool(cr.dbname).get('custom.report.filter').create(cr,uid,form_data)
    #end if field_type:
    return {}

def _set_form_value(self, cr, uid, data, context):
    field_id = data['form']['field_id']
    field_data = pooler.get_pool(cr.dbname).get('ir.model.fields').read(cr,uid,[field_id])[0]
    fields_dict = pooler.get_pool(cr.dbname).get(field_data.get('model')).fields_get(cr,uid,fields=[field_data.get('name')])
    value_field = set_value_fields.get('value')
#   print "fields_dict :",fields_dict.get(field_data.get('name'))
#   set_value_fields['value']= fields_dict.get(field_data.get('name'))
    for k,v in value_field.items():
        if k in ('size','relation','type'):
            del value_field[k]
    field_type = field_data.get('ttype',False)
    if field_type in ('one2many','many2many','many2one'):
        value_field['type'] = 'many2many'
        value_field['relation'] = field_data.get('relation')
    else:
        value_field['type'] = field_type
        if field_type == 'selection':
            selection_data = pooler.get_pool(cr.dbname).get(field_data['model']).fields_get(cr,uid,[field_data['name']])
            value_field['selection'] = selection_data.get(field_data['name']).get('selection')
    operator = (field_type=='many2one') and 'in' or '='
    ret_dict={'field_id':field_id,'operator':operator, 'condition':'and','value':False}  
    return ret_dict

def _set_operator(self, cr, uid, data, context):
    field = pooler.get_pool(cr.dbname).get('ir.model.fields').browse(cr, uid, data['form']['field_id'])
    operator = set_value_fields['operator']['selection']
    while operator: 
        operator.pop(operator.__len__()-1)
        
    if field.ttype == 'many2one':
        operator.append(('in','Equals'))
        operator.append(('in','Contains'))
        operator.append(('not in','Not Contains'))
        operator.append(('is','Is Empty'))
        operator.append(('is not','Is Not Empty'))
    elif field.ttype in ('char', 'text'):
        operator.append(('=','Equals'))
        operator.append(('in','Contains'))
        operator.append(('<>','Not Equals'))
        operator.append(('not in','Not Contains'))
        operator.append(('^','Start With'))
        operator.append(('$','End With'))
        operator.append(('is','Is Empty'))
        operator.append(('is not','Is Not Empty'))
    elif field.ttype in ('date', 'datetime', 'integer', 'float'):
        operator.append(('=','Equals'))
        operator.append(('<>','Not Equals'))
        operator.append(('is','Is Empty'))
        operator.append(('is not','Is Not Empty'))
        operator.append(('<','Smaller'))
        operator.append(('>','Bigger'))
    elif field.ttype in ('boolean', 'selection'):
        operator.append(('=','Equals'))
        operator.append(('<>','Not Equals'))
    return {}

class set_filter_fields(wizard.interface):
    states = {
        'init': {
            'actions': [_set_field_domain],
            'result': {'type':'form', 'arch':select_field_form, 'fields':select_field_fields, 'state':[('end','Cancel'),('set_value_select_field','Continue')]}         
        },
        'set_value_select_field':{
            'actions': [_set_form_value, _set_operator],
            'result': {'type' : 'form', 'arch' : set_value_form, 'fields' : set_value_fields, 'state' : [('end', 'Cancel'),('set_value', 'Confirm Filter') ]}
        },
        'set_value':{
            'actions': [_set_filter_value],
            'result': {'type': 'state', 'state': 'end'}
        }
    }
set_filter_fields("base_report_creator.report_filter.fields")
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

