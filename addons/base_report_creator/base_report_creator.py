# -*- encoding: utf-8 -*-
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

import string
import time
import tools
from osv import fields,osv,orm
from tools.translate import _
from tools import ustr
from tools.safe_eval import safe_eval

#class ir_model_fields(osv.osv):
#   _inherit = 'ir.model.fields'
#   def _get_models(self, cr, uid, model_name, level=1):
#       if not level:
#           return []
#       result = [model_name]
#       print model_name
#       for field,data in self.pool.get(model_name).fields_get(cr, uid).items():
#           if data.get('relation', False):
#               result += self._get_models(cr, uid, data['relation'], level-1)
#       return result
#   def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None):
#       if context and ('model_id' in context):
#           model_name = self.pool.get("ir.model").browse(cr, uid, context['model_id'], context).model
#           models = self._get_models(cr, uid, model_name, context.get('model_level',2))
#           models = map(lambda x: self.pool.get('ir.model').search(cr, uid, [('model','=',x)])[0], models)
#           args.append(('model_id','in',models))
#           print args
#       return super(ir_model_fields, self).search(cr, uid, args, offset, limit, order, context)
#ir_model_fields()


class report_creator(osv.osv):
    _name = "base_report_creator.report"
    _description = "Report"
    model_set_id = False
    #
    # Should request only used fields
    #

    def export_data(self, cr, uid, ids, fields_to_export, context=None):
        data_l = self.read(cr, uid, ids, ['sql_query'], context)
        final_datas = []
        for record in data_l:
            datas = []
            for key in fields_to_export:
                value = record.get(key,'')
                if isinstance(value,tuple):
                    datas.append(ustr(value[1]))
                else:
                    datas.append(ustr(value)) 
            final_datas += [datas]
        return {'datas':final_datas}
        
    def fields_get(self, cr, user, fields=None, context=None):
        if (not context) or 'report_id' not in context:
            return super(report_creator, self).fields_get(cr, user, fields, context)
        report = self.browse(cr, user, context['report_id'])
        models = {}
        for model in report.model_ids:
            models[model.model] = self.pool.get(model.model).fields_get(cr, user, context=context)
        fields = {}
        i = 0
        for f in report.field_ids:
            if f.field_id.model:
                fields['field'+str(i)] = models[f.field_id.model][f.field_id.name]
                i+=1
            else:
                fields['column_count'] = {'readonly': True, 'type': 'integer', 'string': 'Count', 'size': 64, 'name': 'column_count'}
            
        return fields

    #
    # Should Call self.fields_get !
    #
    def fields_view_get(self, cr, user, view_id=None, view_type='form', context=None, toolbar=False):
        if (not context) or 'report_id' not in context:
            return super(report_creator, self).fields_view_get(cr, user, view_id, view_type, context, toolbar)
        report = self.browse(cr, user, context['report_id'])
        models = {}
        for model in report.model_ids:
            models[model.model] = self.pool.get(model.model).fields_get(cr, user, context=context)
        fields = {}
        i = 0
        for f in report.field_ids:
            if f.field_id.model:
                fields['field'+str(i)] = models[f.field_id.model][f.field_id.name]
                i+=1
            else:
                fields['column_count'] = {'readonly': True, 'type': 'integer', 'string': 'Count', 'size': 64, 'name': 'column_count'}
            
        arch = '<?xml version="1.0" encoding="utf-8"?>\n'
        if view_type=='graph':
            orientation_eval = {'horz':'horizontal','vert' :'vertical'}
            orientation = safe_eval(report.view_graph_orientation,orientation_eval)
            arch +='<graph string="%s" type="%s" orientation="%s">' % (report.name, report.view_graph_type, orientation)
            i = 0
            for val in ('x','y'):
                for f in report.field_ids:
                    if f.graph_mode==val:
                        if f.field_id.model:
                            arch += '<field name="%s" select="1"/>' % ('field'+str(i),)
                            i+=1
                        else:
                            arch += '<field name="%s" select="1"/>' % ('column_count',)
                    
        elif view_type=='calendar':
            required_types = ['date_start','date_delay','color']
            set_dict = {'view_type':view_type,'string':report.name}
            temp_list = []
            i=0
            for f in report.field_ids:
                if f.calendar_mode and f.calendar_mode in required_types:
                    if f.field_id.model:
                        field_cal = 'field'+str(i)
                        i+=1
                    else:
                        field_cal = 'column_count'
                    set_dict[f.calendar_mode] = field_cal   
                    del required_types[required_types.index(f.calendar_mode)]
                    
                else:
                    if f.field_id.model:
                        temp_list.append('''<field name="%(name)s" select="1"/>''' % {'name':'field'+str(i)})
                        i+=1
                    else:
                        temp_list.append('''<field name="%(name)s" select="1"/>''' % {'name':'column_count'})    
                    
            arch += '''<%(view_type)s string="%(string)s" date_start="%(date_start)s" ''' %set_dict
            if set_dict.get('date_delay',False):
                arch +=''' date_delay="%(date_delay)s"  '''%set_dict
            
            if set_dict.get('date_stop',False):
                arch +=''' date_stop="%(date_stop)s" '''%set_dict      
            
            if set_dict.get('color',False):
                arch +=''' color="%(color)s"'''%set_dict
            arch += '''>'''
            arch += ''.join(temp_list)
        else:
            arch += '<%s string="%s">\n' % (view_type, report.name)
            i = 0
            for f in report.field_ids:
                if f.field_id.model:
                    arch += '<field name="%s" select="1"/>' % ('field'+str(i),)
                    i+=1
                else:
                    arch += '<field name="%s" select="1"/>' % ('column_count',)
        arch += '</%s>' % (view_type,)
        result = {
            'arch': arch,
            'fields': fields
        }
        result['toolbar'] = {
            'print': [],
            'action': [],
            'relate': []
        }
        return result

    def read(self, cr, user, ids, fields=None, context=None, load='_classic_read'):
        if (not context) or 'report_id' not in context:
            return super(report_creator, self).read(cr, user, ids, fields, context, load)
        ctx = context or {}
        wp = ''
        if self.model_set_id:
            wp = [self._id_get(cr, user, context['report_id'], context)+(' in (%s)' % (','.join(map(lambda x: "'"+str(x)+"'",ids))))]
        report = self._sql_query_get(cr, user, [context['report_id']], 'sql_query', None, ctx, where_plus = wp)
        sql_query = report[context['report_id']]
        cr.execute(sql_query)
        res = cr.dictfetchall()
        fields_get = self.fields_get(cr,user,None,context)
        for r in res:
            for k in r:
                r[k] = r[k] or False
                field_dict = fields_get.get(k)
                field_type = field_dict and field_dict.get('type',False) or False 
                if field_type and field_type == 'many2one':
                    if r[k]==False:
                        continue
                    related_name = self.pool.get(field_dict.get('relation')).name_get(cr,user,[r[k]],context)[0]
                    r[k] = related_name 
        return res

    def search(self, cr, user, args, offset=0, limit=None, order=None, context=None, count=False):
        if (not context) or 'report_id' not in context:
            return super(report_creator, self).search(cr, user, args, offset, limit, order, context, count)
        report = self.browse(cr, user, context['report_id'])
        i = 0
        fields = {}
        for f in report.field_ids:
            if f.field_id.model:
                fields['field'+str(i)] = (f.field_id.model, f.field_id.name)
                i+=1
            else:
                fields['column_count'] = (False, 'Count')   
        newargs = []
        newargs2 = []
        for a in args:
            if fields[a[0]][0]:
                res = self.pool.get(fields[a[0]][0])._where_calc(cr, user, [[fields[a[0]][1],a[1],a[2]]], active_test=False, context=context)
                newargs+=res[0]
                newargs2+=res[1]
            else:
                newargs += [("count(*) " + a[1] +" " + str(a[2]))]
        ctx = context or {}
        ctx['getid'] = True
        report = self._sql_query_get(cr, user, [context['report_id']], 'sql_query', None, ctx, where_plus=newargs, limit=limit, offset=offset)
        query = report[context['report_id']]
        cr.execute(query, newargs2)
        result = cr.fetchall()
        return map(lambda x: x[0], result)

    def _path_get(self,cr, uid, models, filter_ids=[]):
#       ret_str = """   sale_order_line
#   left join sale_order on (sale_order_line.order_id=sale_order.id)
#   left join res_partner on (res_partner.id=sale_order.partner_id)"""
#       where_list = []
#       for filter_id in filter_ids:
#           where_list.append(filter_id.expression)
#       if where_list:
#           ret_str+="\nwhere\n\t"+" and\n\t".join(where_list)
        self.model_set_id = False
        model_dict = {}
        from_list = []
        where_list = []
        filter_list = []
        
#        def _add_inherits(obj):
#            pool_model = self.pool.get(obj)
#            if not model_dict.get(obj,False):
#                model_dict[obj] = pool_model._table
#            for record in pool_model._inherits.keys():
#                     _add_inherits(record)    
        
        for model in models:            
            model_dict[model.model] = self.pool.get(model.model)._table
#            _add_inherits(model.model)
            
        model_list = model_dict.keys()
        reference_model_dict = {}
        for model in model_dict:
            from_list.append(model_dict.get(model))
            rest_list = model_dict.keys()
            rest_list.remove(model)
            model_pool = self.pool.get(model)
            fields_get = model_pool.fields_get(cr,uid)
            model_columns = {}
            
            def _get_inherit_fields(obj):
                pool_model = self.pool.get(obj)
                #Adding the columns of the model itself
                model_columns.update(pool_model._columns)
                #Adding the columns of its _inherits
                for record in pool_model._inherits.keys():
                     _get_inherit_fields(record)

            _get_inherit_fields(model)         
            
            fields_filter = dict(filter(lambda x:x[1].get('relation',False) 
                                        and x[1].get('relation') in rest_list 
                                        and x[1].get('type')=='many2one' 
                                        and not (isinstance(model_columns[x[0]],fields.function) or isinstance(model_columns[x[0]],fields.related)), fields_get.items()))
            if fields_filter:
                model in model_list and model_list.remove(model)
            model_count = reference_model_dict.get(model,False)
            if model_count:
                reference_model_dict[model] = model_count +1
            else:
                reference_model_dict[model] = 1
            for k,v in fields_filter.items():
                v.get('relation') in model_list and model_list.remove(v.get('relation'))
                relation_count = reference_model_dict.get(v.get('relation'),False)
                if relation_count:
                    reference_model_dict[v.get('relation')] = relation_count+1
                else:
                    reference_model_dict[v.get('relation')]=1
                if k in self.pool.get(model)._columns:
                    str_where = model_dict.get(model)+"."+ k + "=" + model_dict.get(v.get('relation'))+'.id'
                    where_list.append(str_where)
        if reference_model_dict:
            self.model_set_id = model_dict.get(reference_model_dict.keys()[reference_model_dict.values().index(min(reference_model_dict.values()))])
        if model_list and not len(model_dict.keys()) == 1:
            raise osv.except_osv(_('No Related Models!!'),_('These is/are model(s) (%s) in selection which is/are not related to any other model') % ','.join(model_list))
        
        if filter_ids and where_list<>[]:
            filter_list.append(' and ')
            filter_list.append(' ')
        
        for filter_id in filter_ids:
            filter_list.append(filter_id.expression)
            filter_list.append(' ')
            filter_list.append(filter_id.condition)
        
        if len(from_list) == 1 and filter_ids:
            from_list.append(' ')
            ret_str = "\n where \n".join(from_list)
        else:
            ret_str = ",\n".join(from_list)
        
            
        if where_list:
            where_list = list(set(where_list))
            ret_str+="\n where \n"+" and\n".join(where_list)
            ret_str = ret_str.strip()
        if filter_list:
            ret_str +="\n".join(filter_list)
            if ret_str.endswith('and'):
                ret_str = ret_str[0:len(ret_str)-3]
            if ret_str.endswith('or'):
                ret_str = ret_str[0:len(ret_str)-2]
            ret_str = ret_str.strip()
        return ret_str % {'uid' : uid}

    def _id_get(self, cr, uid, id, context):
#       return 'min(sale_order_line.id)'
        return self.model_set_id and 'min('+self.model_set_id+'.id)'

    def _sql_query_get(self, cr, uid, ids, prop, unknow_none, context, where_plus=[], limit=None, offset=None):
        result = {}
        for obj in self.browse(cr, uid, ids):
            fields = []
            groupby = []
            i = 0
            for f in obj.field_ids:
                # Allowing to use count(*)
                if not f.field_id.model and f.group_method == 'count':
                    fields.insert(0,('count(*) as column_count'))
                    continue
                t = self.pool.get(f.field_id.model_id.model)._table
                if f.group_method == 'group':
                    fields.append('\t'+t+'.'+f.field_id.name+' as field'+str(i))
                else:
                    fields.append('\t'+f.group_method+'('+t+'.'+f.field_id.name+')'+' as field'+str(i))
                if f.group_method == 'group':
                    groupby.append(t+'.'+f.field_id.name)
                i+=1
            models = self._path_get(cr, uid, obj.model_ids, obj.filter_ids)
            check = self._id_get(cr, uid, ids[0], context)
            if check<>False:
                fields.insert(0,(check+' as id'))
            if models:
                result[obj.id] = """select
    %s
    from
    %s
                """ % (',\n'.join(fields), models)
                if groupby:
                    result[obj.id] += "group by\n\t"+', '.join(groupby)
                if where_plus:
                    result[obj.id] += "\nhaving \n\t"+"\n\t and ".join(where_plus)
                if limit:
                    result[obj.id] += " limit "+str(limit)
                if offset:
                    result[obj.id] += " offset "+str(offset)
            else:
                result[obj.id] = False
        return result
    
    _columns = {
        'name': fields.char('Report Name',size=64, required=True),
        'type': fields.selection([('list','Rows And Columns Report'),], 'Report Type',required=True),#('sum','Summation Report')
        'active': fields.boolean('Active'),
        'view_type1': fields.selection([('form','Form'),('tree','Tree'),('graph','Graph'),('calendar','Calendar')], 'First View', required=True),
        'view_type2': fields.selection([('','/'),('form','Form'),('tree','Tree'),('graph','Graph'),('calendar','Calendar')], 'Second View'),
        'view_type3': fields.selection([('','/'),('form','Form'),('tree','Tree'),('graph','Graph'),('calendar','Calendar')], 'Third View'),
        'view_graph_type': fields.selection([('pie','Pie Chart'),('bar','Bar Chart')], 'Graph Type', required=True),
        'view_graph_orientation': fields.selection([('horz','Horizontal'),('vert','Vertical')], 'Graph Orientation', required=True),
        'model_ids': fields.many2many('ir.model', 'base_report_creator_report_model_rel', 'report_id','model_id', 'Reported Objects'),
        'field_ids': fields.one2many('base_report_creator.report.fields', 'report_id', 'Fields to Display'),
        'filter_ids': fields.one2many('base_report_creator.report.filter', 'report_id', 'Filters'),
        'state': fields.selection([('draft','Draft'),('valid','Valid')], 'Status', required=True),
        'sql_query': fields.function(_sql_query_get, method=True, type="text", string='SQL Query', store=True),
        'group_ids': fields.many2many('res.groups', 'base_report_creator_group_rel','report_id','group_id','Authorized Groups'),
    }
    _defaults = {
        'type': lambda *args: 'list',
        'state': lambda *args: 'draft',
        'active': lambda *args: True,
        'view_type1': lambda *args: 'tree',
        'view_type2': lambda *args: 'graph',
        'view_graph_type': lambda *args: 'bar',
        'view_graph_orientation': lambda *args: 'horz',
    }
    def _function_field(self, cr, uid, ids):
        this_objs = self.browse(cr, uid, ids)
        for obj in this_objs:
            for fld in obj.field_ids:
                # Allowing to use count(*)
                if not fld.field_id.model and fld.group_method == 'count':
                    continue
                model_column = self.pool.get(fld.field_id.model)._columns[fld.field_id.name]
                if (isinstance(model_column,fields.function) or isinstance(model_column,fields.related)) and not model_column.store:
                    return False 
        return True
    
    def _aggregation_error(self, cr, uid, ids):
        aggregate_columns = ('integer','float')
        apply_functions = ('sum','min','max','avg','count')
        this_objs = self.browse(cr, uid, ids)
        for obj in this_objs:
            for fld in obj.field_ids:
                # Allowing to use count(*)
                if not fld.field_id.model and fld.group_method == 'count':
                    continue
                model_column = self.pool.get(fld.field_id.model)._columns[fld.field_id.name]                
                if model_column._type not in aggregate_columns and fld.group_method in apply_functions:
                    return False 
        return True
    
    def _calander_view_error(self, cr, uid, ids):
#       required_types = ['date_start','date_delay','color'] 
        required_types = []
        this_objs = self.browse(cr, uid, ids)
        for obj in this_objs:
            if obj.view_type1=='calendar' or obj.view_type2=='calendar' or obj.view_type3=='calendar': 
                for fld in obj.field_ids:
                    # Allowing to use count(*)
                    if not fld.field_id.model and fld.group_method == 'count':
                        continue
                    model_column = self.pool.get(fld.field_id.model)._columns[fld.field_id.name]
                    if fld.calendar_mode in ('date_start','date_end') and model_column._type not in ('date','datetime'):
                        return False
                    elif fld.calendar_mode=='date_delay' and model_column._type not in ('int','float'):
                        return False
                    else:
                        required_types.append(fld.calendar_mode)
                if 'date_start' not in required_types:
                    return False     
        return True
    
    _constraints = [
        (_function_field, 'You can not display field which are not stored in Database.', ['field_ids']),
        (_aggregation_error, 'You can apply aggregate function to the non calculated field.', ['field_ids']),
        (_calander_view_error, "You must have to give calendar view's color,start date and delay.", ['field_ids']),
    ]
report_creator()

class report_creator_field(osv.osv):
    _name = "base_report_creator.report.fields"
    _description = "Display Fields"
    _rec_name = 'field_id'
    _order = "sequence,id"
    _columns = {
        'sequence': fields.integer('Sequence'),
        'field_id': fields.many2one('ir.model.fields', 'Field'),
        'report_id': fields.many2one('base_report_creator.report','Report', on_delete='cascade'),
        'group_method': fields.selection([('group','Grouped'),('sum','Sum'),('min','Minimum'),('count','Count'),('max','Maximum'),('avg','Average')], 'Grouping Method', required=True),
        'graph_mode': fields.selection([('','/'),('x','X Axis'),('y','Y Axis')], 'Graph Mode'),
        'calendar_mode': fields.selection([('','/'),('date_start','Starting Date'),('date_end','Ending Date'),('date_delay','Delay'),('date_stop','End Date'),('color','Unique Colors')], 'Calendar Mode'),
    }
    _defaults = {
        'group_method': lambda *args: 'group',
        'graph_mode': lambda *args: '',
    }
report_creator_field()

class report_creator_filter(osv.osv):
    _name = "base_report_creator.report.filter"
    _description = "Report Filters"
    _columns = {
        'name': fields.char('Filter Name',size=64, required=True),
        'expression': fields.text('Value', required=True,help='Provide an expression for the field based on which you want to filter the records.\n e.g. res_partner.id=3'),
        'report_id': fields.many2one('base_report_creator.report','Report', on_delete='cascade'),
        'condition' : fields.selection([('and','AND'),('or','OR')], 'Condition')
    }
    _defaults = {
        'condition': lambda *args: 'and',
    }
report_creator_filter()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

