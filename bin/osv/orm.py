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

#
# Object relationnal mapping to postgresql module
#    . Hierarchical structure
#    . Constraints consistency, validations
#    . Object meta Data depends on its status
#    . Optimised processing by complex query (multiple actions at once)
#    . Default fields value
#    . Permissions optimisation
#    . Persistant object: DB postgresql
#    . Datas conversions
#    . Multi-level caching system
#    . 2 different inheritancies
#    . Fields:
#         - classicals (varchar, integer, boolean, ...)
#         - relations (one2many, many2one, many2many)
#         - functions
#
#

import time
import calendar
import datetime
import types
import string
import netsvc
import re

import pickle

import fields
import tools
from tools.translate import _

import copy
import sys
import operator

try:
    from lxml import etree
except ImportError:
    sys.stderr.write("ERROR: Import lxml module\n")
    sys.stderr.write("ERROR: Try to install the python-lxml package\n")

from tools.config import config

regex_order = re.compile('^(([a-z0-9_]+|"[a-z0-9_]+")( *desc| *asc)?( *, *|))+$', re.I)

def last_day_of_current_month():
    today = datetime.date.today()
    last_day = str(calendar.monthrange(today.year, today.month)[1])
    return time.strftime('%Y-%m-' + last_day)

def intersect(la, lb):
    return filter(lambda x: x in lb, la)

class except_orm(Exception):
    def __init__(self, name, value):
        self.name = name
        self.value = value
        self.args = (name, value)

class BrowseRecordError(Exception):
    pass

# Readonly python database object browser
class browse_null(object):

    def __init__(self):
        self.id = False

    def __getitem__(self, name):
        return False

    def __getattr__(self, name):
        return False  # XXX: return self ?

    def __int__(self):
        return False

    def __str__(self):
        return ''

    def __nonzero__(self):
        return False

    def __unicode__(self):
        return u''


#
# TODO: execute an object method on browse_record_list
#
class browse_record_list(list):

    def __init__(self, lst, context=None):
        if not context:
            context = {}
        super(browse_record_list, self).__init__(lst)
        self.context = context


class browse_record(object):
    def __init__(self, cr, uid, id, table, cache, context=None, list_class = None, fields_process={}):
        '''
        table : the object (inherited from orm)
        context : a dictionary with an optional context
        '''
        if not context:
            context = {}
        self._list_class = list_class or browse_record_list
        self._cr = cr
        self._uid = uid
        self._id = id
        self._table = table
        self._table_name = self._table._name
        self._context = context
        self._fields_process = fields_process

        cache.setdefault(table._name, {})
        self._data = cache[table._name]

        if not (id and isinstance(id, (int, long,))):
            raise BrowseRecordError(_('Wrong ID for the browse record, got %r, expected an integer.') % (id,))
#        if not table.exists(cr, uid, id, context):
#            raise BrowseRecordError(_('Object %s does not exists') % (self,))

        if id not in self._data:
            self._data[id] = {'id': id}

        self._cache = cache

    def __getitem__(self, name):
        if name == 'id':
            return self._id
        if name not in self._data[self._id]:
            # build the list of fields we will fetch

            # fetch the definition of the field which was asked for
            if name in self._table._columns:
                col = self._table._columns[name]
            elif name in self._table._inherit_fields:
                col = self._table._inherit_fields[name][2]
            elif hasattr(self._table, name):
                if isinstance(getattr(self._table, name), (types.MethodType, types.LambdaType, types.FunctionType)):
                    return lambda *args, **argv: getattr(self._table, name)(self._cr, self._uid, [self._id], *args, **argv)
                else:
                    return getattr(self._table, name)
            else:
                logger = netsvc.Logger()
                logger.notifyChannel('orm', netsvc.LOG_ERROR, "Programming error: field '%s' does not exist in object '%s' !" % (name, self._table._name))
                return False

            # if the field is a classic one or a many2one, we'll fetch all classic and many2one fields
            if col._prefetch:
                # gen the list of "local" (ie not inherited) fields which are classic or many2one
                ffields = filter(lambda x: x[1]._classic_write, self._table._columns.items())
                # gen the list of inherited fields
                inherits = map(lambda x: (x[0], x[1][2]), self._table._inherit_fields.items())
                # complete the field list with the inherited fields which are classic or many2one
                ffields += filter(lambda x: x[1]._classic_write, inherits)
            # otherwise we fetch only that field
            else:
                ffields = [(name, col)]
            ids = filter(lambda id: name not in self._data[id], self._data.keys())
            # read the data
            fffields = map(lambda x: x[0], ffields)
            datas = self._table.read(self._cr, self._uid, ids, fffields, context=self._context, load="_classic_write")
            if self._fields_process:
                lang = self._context.get('lang', 'en_US') or 'en_US'
                lang_obj_ids = self.pool.get('res.lang').search(self._cr, self._uid,[('code','=',lang)])
                if not lang_obj_ids:
                    raise Exception(_('Language with code "%s" is not defined in your system !\nDefine it through the Administration menu.') % (lang,))
                lang_obj = self.pool.get('res.lang').browse(self._cr, self._uid,lang_obj_ids[0])
                for n, f in ffields:
                    if f._type in self._fields_process:
                        for d in datas:
                            d[n] = self._fields_process[f._type](d[n])
                            if (d[n] is not None) and (d[n] is not False):
                                d[n].set_value(self._cr, self._uid, d[n], self, f, lang_obj)


            # create browse records for 'remote' objects
            for data in datas:
                new_data = {}
                for n, f in ffields:
                    if f._type in ('many2one', 'one2one'):
                        if data[n]:
                            obj = self._table.pool.get(f._obj)
                            if type(data[n]) in (type([]),type( (1,) )):
                                ids2 = data[n][0]
                            else:
                                ids2 = data[n]
                            if ids2:
                                # FIXME: this happen when a _inherits object
                                #        overwrite a field of it parent. Need
                                #        testing to be sure we got the right
                                #        object and not the parent one.
                                if not isinstance(ids2, browse_record):
                                    new_data[n] = browse_record(self._cr,
                                        self._uid, ids2, obj, self._cache,
                                        context=self._context,
                                        list_class=self._list_class,
                                        fields_process=self._fields_process)
                            else:
                                new_data[n] = browse_null()
                        else:
                            new_data[n] = browse_null()
                    elif f._type in ('one2many', 'many2many') and len(data[n]):
                        new_data[n] = self._list_class([browse_record(self._cr, self._uid, id, self._table.pool.get(f._obj), self._cache, context=self._context, list_class=self._list_class, fields_process=self._fields_process) for id in data[n]], self._context)
                    else:
                        new_data[n] = data[n]
                self._data[data['id']].update(new_data)
        return self._data[self._id][name]

    def __getattr__(self, name):
#       raise an AttributeError exception.
        return self[name]

    def __contains__(self, name):
        return (name in self._table._columns) or (name in self._table._inherit_fields) or hasattr(self._table, name)

    def __hasattr__(self, name):
        return name in self

    def __int__(self):
        return self._id

    def __str__(self):
        return "browse_record(%s, %d)" % (self._table_name, self._id)

    def __eq__(self, other):
        return (self._table_name, self._id) == (other._table_name, other._id)

    def __ne__(self, other):
        return (self._table_name, self._id) != (other._table_name, other._id)

    # we need to define __unicode__ even though we've already defined __str__
    # because we have overridden __getattr__
    def __unicode__(self):
        return unicode(str(self))

    def __hash__(self):
        return hash((self._table_name, self._id))

    __repr__ = __str__


def get_pg_type(f):
    '''
    returns a tuple
    (type returned by postgres when the column was created, type expression to create the column)
    '''

    type_dict = {
            fields.boolean: 'bool',
            fields.integer: 'int4',
            fields.integer_big: 'int8',
            fields.text: 'text',
            fields.date: 'date',
            fields.time: 'time',
            fields.datetime: 'timestamp',
            fields.binary: 'bytea',
            fields.many2one: 'int4',
            }
    if type(f) in type_dict:
        f_type = (type_dict[type(f)], type_dict[type(f)])
    elif isinstance(f, fields.float):
        if f.digits:
            f_type = ('numeric', 'NUMERIC(%d,%d)' % (f.digits[0], f.digits[1]))
        else:
            f_type = ('float8', 'DOUBLE PRECISION')
    elif isinstance(f, (fields.char, fields.reference)):
        f_type = ('varchar', 'VARCHAR(%d)' % (f.size,))
    elif isinstance(f, fields.selection):
        if isinstance(f.selection, list) and isinstance(f.selection[0][0], (str, unicode)):
            f_size = reduce(lambda x, y: max(x, len(y[0])), f.selection, f.size or 16)
        elif isinstance(f.selection, list) and isinstance(f.selection[0][0], int):
            f_size = -1
        else:
            f_size = (hasattr(f, 'size') and f.size) or 16

        if f_size == -1:
            f_type = ('int4', 'INTEGER')
        else:
            f_type = ('varchar', 'VARCHAR(%d)' % f_size)
    elif isinstance(f, fields.function) and eval('fields.'+(f._type)) in type_dict:
        t = eval('fields.'+(f._type))
        f_type = (type_dict[t], type_dict[t])
    elif isinstance(f, fields.function) and f._type == 'float':
        if f.digits:
            f_type = ('numeric', 'NUMERIC(%d,%d)' % (f.digits[0], f.digits[1]))
        else:
            f_type = ('float8', 'DOUBLE PRECISION')
    elif isinstance(f, fields.function) and f._type == 'selection':
        f_type = ('text', 'text')
    elif isinstance(f, fields.function) and f._type == 'char':
        f_type = ('varchar', 'VARCHAR(%d)' % (f.size))
    else:
        logger = netsvc.Logger()
        logger.notifyChannel("init", netsvc.LOG_WARNING, '%s type not supported!' % (type(f)))
        f_type = None
    return f_type


class orm_template(object):
    _name = None
    _columns = {}
    _constraints = []
    _defaults = {}
    _rec_name = 'name'
    _parent_name = 'parent_id'
    _parent_store = False
    _parent_order = False
    _date_name = 'date'
    _order = 'id'
    _sequence = None
    _description = None
    _inherits = {}
    _table = None
    _invalids = set()

    CONCURRENCY_CHECK_FIELD = '__last_update'

    def _field_create(self, cr, context={}):
        cr.execute("SELECT id FROM ir_model WHERE model=%s", (self._name,))
        if not cr.rowcount:
            cr.execute('SELECT nextval(%s)', ('ir_model_id_seq',))
            model_id = cr.fetchone()[0]
            cr.execute("INSERT INTO ir_model (id,model, name, info,state) VALUES (%s, %s, %s, %s, %s)", (model_id, self._name, self._description, self.__doc__, 'base'))
        else:
            model_id = cr.fetchone()[0]
        if 'module' in context:
            name_id = 'model_'+self._name.replace('.','_')
            cr.execute('select * from ir_model_data where name=%s and res_id=%s', (name_id,model_id))
            if not cr.rowcount:
                cr.execute("INSERT INTO ir_model_data (name,date_init,date_update,module,model,res_id) VALUES (%s, now(), now(), %s, %s, %s)", \
                    (name_id, context['module'], 'ir.model', model_id)
                )

        cr.commit()

        cr.execute("SELECT * FROM ir_model_fields WHERE model=%s", (self._name,))
        cols = {}
        for rec in cr.dictfetchall():
            cols[rec['name']] = rec

        for (k, f) in self._columns.items():
            vals = {
                'model_id': model_id,
                'model': self._name,
                'name': k,
                'field_description': f.string.replace("'", " "),
                'ttype': f._type,
                'relation': f._obj or 'NULL',
                'view_load': (f.view_load and 1) or 0,
                'select_level': tools.ustr(f.select or 0),
                'readonly':(f.readonly and 1) or 0,
                'required':(f.required and 1) or 0,
                'relation_field': (f._type=='one2many' and isinstance(f,fields.one2many)) and f._fields_id or '',
            }
            # When its a custom field,it does not contain f.select
            if context.get('field_state','base') == 'manual':
                if context.get('field_name','') == k:
                    vals['select_level'] = context.get('select','0')
                #setting value to let the problem NOT occur next time
                else:
                    vals['select_level'] = cols[k]['select_level']
            
            if k not in cols:
                cr.execute('select nextval(%s)', ('ir_model_fields_id_seq',))
                id = cr.fetchone()[0]
                vals['id'] = id
                cr.execute("""INSERT INTO ir_model_fields (
                    id, model_id, model, name, field_description, ttype,
                    relation,view_load,state,select_level,relation_field
                ) VALUES (
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
                )""", (
                    id, vals['model_id'], vals['model'], vals['name'], vals['field_description'], vals['ttype'],
                     vals['relation'], bool(vals['view_load']), 'base',
                    vals['select_level'],vals['relation_field']
                ))
                if 'module' in context:
                    name1 = 'field_' + self._table + '_' + k
                    cr.execute("select name from ir_model_data where name=%s", (name1,))
                    if cr.fetchone():
                        name1 = name1 + "_" + str(id)
                    cr.execute("INSERT INTO ir_model_data (name,date_init,date_update,module,model,res_id) VALUES (%s, now(), now(), %s, %s, %s)", \
                        (name1, context['module'], 'ir.model.fields', id)
                    )
            else:
                for key, val in vals.items():
                    if cols[k][key] != vals[key]:
                        cr.execute('update ir_model_fields set field_description=%s where model=%s and name=%s', (vals['field_description'], vals['model'], vals['name']))
                        cr.commit()
                        cr.execute("""UPDATE ir_model_fields SET
                            model_id=%s, field_description=%s, ttype=%s, relation=%s,
                            view_load=%s, select_level=%s, readonly=%s ,required=%s ,relation_field=%s
                        WHERE
                            model=%s AND name=%s""", (
                                vals['model_id'], vals['field_description'], vals['ttype'],
                                vals['relation'], bool(vals['view_load']),
                                vals['select_level'], bool(vals['readonly']),bool(vals['required']), vals['relation_field'], vals['model'], vals['name']
                            ))
                        continue
        cr.commit()

    def _auto_init(self, cr, context={}):
        self._field_create(cr, context)

    def __init__(self, cr):
        if not self._name and not hasattr(self, '_inherit'):
            name = type(self).__name__.split('.')[0]
            msg = "The class %s has to have a _name attribute" % name

            logger = netsvc.Logger()
            logger.notifyChannel('orm', netsvc.LOG_ERROR, msg )
            raise except_orm('ValueError', msg )

        if not self._description:
            self._description = self._name
        if not self._table:
            self._table = self._name.replace('.', '_')

    def browse(self, cr, uid, select, context=None, list_class=None, fields_process={}):
        if not context:
            context = {}
        self._list_class = list_class or browse_record_list
        cache = {}
        # need to accepts ints and longs because ids coming from a method
        # launched by button in the interface have a type long...
        if isinstance(select, (int, long)):
            return browse_record(cr, uid, select, self, cache, context=context, list_class=self._list_class, fields_process=fields_process)
        elif isinstance(select, list):
            return self._list_class([browse_record(cr, uid, id, self, cache, context=context, list_class=self._list_class, fields_process=fields_process) for id in select], context)
        else:
            return browse_null()

    def __export_row(self, cr, uid, row, fields, context=None):
        
        def check_type(field_type):
            if field_type == 'float':
                return 0.0
            elif field_type == 'integer':
                return 0
            elif field_type == 'boolean':   
                return False                                
            return ''
        
        def selection_field(in_field):
            col_obj = self.pool.get(in_field.keys()[0])
            if f[i] in col_obj._columns.keys():
                return  col_obj._columns[f[i]]
            elif f[i] in col_obj._inherits.keys():
                selection_field(col_obj._inherits)
            else:
                return False    
           
        lines = []
        data = map(lambda x: '', range(len(fields)))
        done = []
        for fpos in range(len(fields)):
            f = fields[fpos]            
            if f:
                r = row
                i = 0
                while i < len(f):
                    if f[i] == 'db_id':
                        r = r['id']                        
                    elif f[i] == 'id':                        
                        model_data = self.pool.get('ir.model.data')
                        data_ids = model_data.search(cr, uid, [('model','=',r._table_name),('res_id','=',r['id'])])
                        if len(data_ids):
                            d = model_data.read(cr, uid, data_ids, ['name','module'])[0]
                            if d['module']:
                                r = '%s.%s'%(d['module'],d['name'])
                            else:
                                r = d['name']
                        else:
                            break
                    else:
                        r = r[f[i]]
                        # To display external name of selection field when its exported
                        if not context.get('import_comp',False):# Allow external name only if its not import compatible 
                            cols = False
                            if f[i] in self._columns.keys():
                                cols = self._columns[f[i]]
                            elif f[i] in self._inherit_fields.keys():
                                cols = selection_field(self._inherits)
                            if cols and cols._type == 'selection':
                                sel_list = cols.selection
                                if type(sel_list) == type([]):
                                    r = [x[1] for x in sel_list if r==x[0]][0]

                    if not r:
                        if f[i] in self._columns: 
                            r = check_type(self._columns[f[i]]._type)
                        elif f[i] in self._inherit_fields:
                            r = check_type(self._inherit_fields[f[i]][2]._type)                        
                        data[fpos] = r                        
                        break
                    if isinstance(r, (browse_record_list, list)):
                        first = True
                        fields2 = map(lambda x: (x[:i+1]==f[:i+1] and x[i+1:]) \
                                or [], fields)
                        if fields2 in done:
                            break
                        done.append(fields2)                        
                        for row2 in r:
                            lines2 = self.__export_row(cr, uid, row2, fields2,
                                    context)                            
                            if first:
                                for fpos2 in range(len(fields)):
                                    if lines2 and lines2[0][fpos2]:
                                        data[fpos2] = lines2[0][fpos2]
                                if not data[fpos]:
                                    dt = ''
                                    for rr in r :
                                        if isinstance(rr.name, browse_record):
                                            rr = rr.name
                                        rr_name = self.pool.get(rr._table_name).name_get(cr, uid, [rr.id])
                                        rr_name = rr_name and rr_name[0] and rr_name[0][1] or ''
                                        dt += tools.ustr(rr_name or '') + ','
                                    data[fpos] = dt[:-1]
                                    break
                                lines += lines2[1:]
                                first = False
                            else:
                                lines += lines2                            
                        break
                    i += 1
                if i == len(f):
                    if isinstance(r, browse_record):
                        r = self.pool.get(r._table_name).name_get(cr, uid, [r.id])
                        r = r and r[0] and r[0][1] or ''
                    data[fpos] = tools.ustr(r or '')
        return [data] + lines

    def export_data(self, cr, uid, ids, fields_to_export, context=None):
        if not context:
            context = {}
        imp_comp = context.get('import_comp',False)        
        cols = self._columns.copy()
        for f in self._inherit_fields:
            cols.update({f: self._inherit_fields[f][2]})        
        fields_to_export = map(lambda x: x.split('/'), fields_to_export)
        fields_export = fields_to_export+[]        
        warning = ''  
        warning_fields = []      
        for field in fields_export:
            if imp_comp and len(field)>1:
                warning_fields.append('/'.join(map(lambda x:x in cols and cols[x].string or x,field)))
            elif len (field) <=1:
                if imp_comp and cols.get(field and field[0],False):
                    if ((isinstance(cols[field[0]], fields.function) and not cols[field[0]].store) \
                                     or isinstance(cols[field[0]], fields.related)\
                                     or isinstance(cols[field[0]], fields.one2many)):                        
                        warning_fields.append('/'.join(map(lambda x:x in cols and cols[x].string or x,field)))
        datas = []
        if imp_comp and len(warning_fields):
            warning = 'Following columns cannot be exported since you select to be import compatible.\n%s' %('\n'.join(warning_fields))        
            cr.rollback()
            return {'warning' : warning}
        for row in self.browse(cr, uid, ids, context):
            datas += self.__export_row(cr, uid, row, fields_to_export, context)
        return {'datas':datas}

    def import_data(self, cr, uid, fields, datas, mode='init', current_module='', noupdate=False, context=None, filename=None):
        if not context:
            context = {}
        fields = map(lambda x: x.split('/'), fields)
        logger = netsvc.Logger()
        ir_model_data_obj = self.pool.get('ir.model.data')
        
        def _check_db_id(self, model_name, db_id):
            obj_model = self.pool.get(model_name)
            ids = obj_model.search(cr, uid, [('id','=',int(db_id))])
            if not len(ids):
                raise Exception(_("Database ID doesn't exist: %s : %s") %(model_name, db_id))
            return True
            
        def process_liness(self, datas, prefix, current_module, model_name, fields_def, position=0):
            line = datas[position]
            row = {}
            translate = {}
            todo = []
            warning = []
            data_id = False
            data_res_id = False
            is_xml_id = False
            is_db_id = False
            ir_model_data_obj = self.pool.get('ir.model.data')
            #
            # Import normal fields
            #
            for i in range(len(fields)):
                if i >= len(line):
                    raise Exception(_('Please check that all your lines have %d columns.') % (len(fields),))
                if not line[i]:
                    continue
                    
                field = fields[i]
                if prefix and not prefix[0] in field:
                    continue
                
                if (len(field)==len(prefix)+1) and field[len(prefix)].endswith(':db_id'):
                        # Database ID
                        res = False
                        if line[i]:
                            field_name = field[0].split(':')[0]
                            model_rel =  fields_def[field_name]['relation']                            
                            
                            if fields_def[field[len(prefix)][:-6]]['type']=='many2many':
                                res_id = []
                                for db_id in line[i].split(config.get('csv_internal_sep')):
                                    try:
                                        _check_db_id(self, model_rel, db_id)
                                        res_id.append(db_id)
                                    except Exception,e:                                    
                                        warning += [tools.exception_to_unicode(e)]
                                        logger.notifyChannel("import", netsvc.LOG_ERROR,
                                                  tools.exception_to_unicode(e))
                                if len(res_id):
                                    res = [(6, 0, res_id)]
                            else:
                                try:
                                    _check_db_id(self, model_rel, line[i])
                                    res = line[i]
                                except Exception,e:                                    
                                    warning += [tools.exception_to_unicode(e)]
                                    logger.notifyChannel("import", netsvc.LOG_ERROR,
                                              tools.exception_to_unicode(e))                        
                        row[field_name] = res or False
                        continue

                if (len(field)==len(prefix)+1) and field[len(prefix)].endswith(':id'):
                    res_id = False
                    if line[i]:
                        if fields_def[field[len(prefix)][:-3]]['type']=='many2many':
                            res_id = []
                            for word in line[i].split(config.get('csv_internal_sep')):
                                if '.' in word:
                                    module, xml_id = word.rsplit('.', 1)
                                else:
                                    module, xml_id = current_module, word                                
                                id = ir_model_data_obj._get_id(cr, uid, module,
                                        xml_id)
                                res_id2 = ir_model_data_obj.read(cr, uid, [id],
                                        ['res_id'])[0]['res_id']
                                if res_id2:
                                    res_id.append(res_id2)
                            if len(res_id):
                                res_id = [(6, 0, res_id)]
                        else:
                            if '.' in line[i]:
                                module, xml_id = line[i].rsplit('.', 1)
                            else:
                                module, xml_id = current_module, line[i]                            
                            id = ir_model_data_obj._get_id(cr, uid, module, xml_id)
                            res_id = ir_model_data_obj.read(cr, uid, [id],
                                    ['res_id'])[0]['res_id']
                    row[field[-1][:-3]] = res_id or False
                    continue
                if (len(field) == len(prefix)+1) and \
                        len(field[len(prefix)].split(':lang=')) == 2:
                    f, lang = field[len(prefix)].split(':lang=')
                    translate.setdefault(lang, {})[f]=line[i] or False
                    continue
                if (len(field) == len(prefix)+1) and \
                        (prefix == field[0:len(prefix)]):
                    if field[len(prefix)] == "id":  
                        # XML ID                         
                        db_id = False                 
                        is_xml_id = data_id = line[i] 
                        d =  data_id.split('.')
                        module = len(d)>1 and d[0] or ''
                        name = len(d)>1 and d[1] or d[0] 
                        data_ids = ir_model_data_obj.search(cr, uid, [('module','=',module),('model','=',model_name),('name','=',name)])                    
                        if len(data_ids):
                            d = ir_model_data_obj.read(cr, uid, data_ids, ['res_id'])[0]                                                
                            db_id = d['res_id']                       
                        if is_db_id and not db_id:
                           data_ids = ir_model_data_obj.search(cr, uid, [('module','=',module),('model','=',model_name),('res_id','=',is_db_id)])                     
                           if not len(data_ids):
                               ir_model_data_obj.create(cr, uid, {'module':module, 'model':model_name, 'name':name, 'res_id':is_db_id}) 
                               db_id = is_db_id 
                        if is_db_id and int(db_id) != int(is_db_id):                        
                            warning += [_("Id is not the same than existing one: %s")%(is_db_id)]
                            logger.notifyChannel("import", netsvc.LOG_ERROR,
                                    _("Id is not the same than existing one: %s")%(is_db_id))
                        continue

                    if field[len(prefix)] == "db_id":
                        # Database ID                        
                        try:                            
                            _check_db_id(self, model_name, line[i])
                            data_res_id = is_db_id = int(line[i])
                        except Exception,e:
                            warning += [tools.exception_to_unicode(e)]
                            logger.notifyChannel("import", netsvc.LOG_ERROR,
                                      tools.exception_to_unicode(e))
                            continue
                        data_ids = ir_model_data_obj.search(cr, uid, [('model','=',model_name),('res_id','=',line[i])])
                        if len(data_ids):
                            d = ir_model_data_obj.read(cr, uid, data_ids, ['name','module'])[0]                                                
                            data_id = d['name']       
                            if d['module']:
                                data_id = '%s.%s'%(d['module'],d['name'])
                            else:
                                data_id = d['name']
                        if is_xml_id and not data_id:
                            data_id = is_xml_id                                     
                        if is_xml_id and is_xml_id!=data_id:  
                            warning += [_("Id is not the same than existing one: %s")%(line[i])]
                            logger.notifyChannel("import", netsvc.LOG_ERROR,
                                    _("Id is not the same than existing one: %s")%(line[i]))
                                                           
                        continue
                    if fields_def[field[len(prefix)]]['type'] == 'integer':
                        res = line[i] and int(line[i])
                    elif fields_def[field[len(prefix)]]['type'] == 'boolean':
                        res = line[i].lower() not in ('0', 'false', 'off')
                    elif fields_def[field[len(prefix)]]['type'] == 'float':
                        res = line[i] and float(line[i])
                    elif fields_def[field[len(prefix)]]['type'] == 'selection':
                        res = False
                        if isinstance(fields_def[field[len(prefix)]]['selection'],
                                (tuple, list)):
                            sel = fields_def[field[len(prefix)]]['selection']
                        else:
                            sel = fields_def[field[len(prefix)]]['selection'](self,
                                    cr, uid, context)
                        for key, val in sel:
                            if line[i] in [tools.ustr(key),tools.ustr(val)]: #Acepting key or value for selection field
                                res = key
                                break
                        if line[i] and not res:
                            logger.notifyChannel("import", netsvc.LOG_WARNING,
                                    _("key '%s' not found in selection field '%s'") % \
                                            (line[i], field[len(prefix)]))
                            
                            warning += [_("Key/value '%s' not found in selection field '%s'")%(line[i],field[len(prefix)])]
                            
                    elif fields_def[field[len(prefix)]]['type']=='many2one':
                        res = False
                        if line[i]:
                            relation = fields_def[field[len(prefix)]]['relation']
                            res2 = self.pool.get(relation).name_search(cr, uid,
                                    line[i], [], operator='=', context=context)
                            res = (res2 and res2[0][0]) or False
                            if not res:
                                warning += [_("Relation not found: %s on '%s'")%(line[i],relation)]
                                logger.notifyChannel("import", netsvc.LOG_WARNING,
                                        _("Relation not found: %s on '%s'")%(line[i],relation))
                    elif fields_def[field[len(prefix)]]['type']=='many2many':
                        res = []
                        if line[i]:
                            relation = fields_def[field[len(prefix)]]['relation']
                            for word in line[i].split(config.get('csv_internal_sep')):
                                res2 = self.pool.get(relation).name_search(cr,
                                        uid, word, [], operator='=', context=context)
                                res3 = (res2 and res2[0][0]) or False
                                if not res3:
                                    warning += [_("Relation not found: %s on '%s'")%(line[i],relation)]
                                    logger.notifyChannel("import",
                                            netsvc.LOG_WARNING,
                                            _("Relation not found: %s on '%s'")%(line[i],relation))
                                else:
                                    res.append(res3)
                            if len(res):
                                res = [(6, 0, res)]
                    else:
                        res = line[i] or False
                    row[field[len(prefix)]] = res
                elif (prefix==field[0:len(prefix)]):
                    if field[0] not in todo:
                        todo.append(field[len(prefix)])
            #
            # Import one2many, many2many fields
            #
            nbrmax = 1
            for field in todo:
                relation_obj = self.pool.get(fields_def[field]['relation'])
                newfd = relation_obj.fields_get(
                        cr, uid, context=context)
                res = process_liness(self, datas, prefix + [field], current_module, relation_obj._name, newfd, position)                              
                (newrow, max2, w2, translate2, data_id2, data_res_id2) = res                  
                nbrmax = max(nbrmax, max2)
                warning = warning + w2         
                reduce(lambda x, y: x and y, newrow)       
                row[field] = (reduce(lambda x, y: x or y, newrow.values()) and \
                        [(0, 0, newrow)]) or []                
                i = max2
                while (position+i)<len(datas):
                    ok = True
                    for j in range(len(fields)):
                        field2 = fields[j]
                        if (len(field2) <= (len(prefix)+1)) and datas[position+i][j]:
                            ok = False
                    if not ok:
                        break

                    (newrow, max2, w2, translate2, data_id2, data_res_id2) = process_liness(
                            self, datas, prefix+[field], current_module, relation_obj._name, newfd, position+i)
                    warning = warning+w2
                    if reduce(lambda x, y: x or y, newrow.values()):
                        row[field].append((0, 0, newrow))                    
                    i += max2
                    nbrmax = max(nbrmax, i)

            if len(prefix)==0:
                for i in range(max(nbrmax, 1)):
                    #if datas:
                    datas.pop(0)
            result = (row, nbrmax, warning, translate, data_id, data_res_id)
            return result

        fields_def = self.fields_get(cr, uid, context=context)
        done = 0

        initial_size = len(datas)
        if config.get('import_partial', False) and filename:
            data = pickle.load(file(config.get('import_partial')))
            original_value =  data.get(filename, 0)
        counter = 0
        while len(datas):
            counter += 1
            res = {}
            #try:
            (res, other, warning, translate, data_id, res_id) = \
                    process_liness(self, datas, [], current_module, self._name, fields_def)
            if len(warning):
                cr.rollback()
                return (-1, res, 'Line ' + str(counter) +' : ' + '!\n'.join(warning), '')

            try:
                id = ir_model_data_obj._update(cr, uid, self._name,
                     current_module, res, xml_id=data_id, mode=mode,
                     noupdate=noupdate, res_id=res_id, context=context)
            except Exception, e:
                import psycopg2
                import osv
                cr.rollback()
                if isinstance(e,psycopg2.IntegrityError):
                    msg= _('Insertion Failed! ')
                    for key in self.pool._sql_error.keys():
                        if key in e[0]:
                            msg = self.pool._sql_error[key]
                            break
                    return (-1, res, 'Line ' + str(counter) +' : ' + msg, '' )
                if isinstance(e, osv.orm.except_orm ):
                    msg = _('Insertion Failed! ' + e[1])
                    return (-1, res, 'Line ' + str(counter) +' : ' + msg, '' )
                #Raising Uncaught exception
                raise
            for lang in translate:
                context2 = context.copy()
                context2['lang'] = lang
                self.write(cr, uid, [id], translate[lang], context2)
            if config.get('import_partial', False) and filename and (not (counter%100)) :
                data = pickle.load(file(config.get('import_partial')))
                data[filename] = initial_size - len(datas) + original_value
                pickle.dump(data, file(config.get('import_partial'),'wb'))
                if context.get('defer_parent_store_computation'):
                    self._parent_store_compute(cr)
                cr.commit()

            #except Exception, e:
            #    logger.notifyChannel("import", netsvc.LOG_ERROR, e)
            #    cr.rollback()
            #    try:
            #        return (-1, res, e[0], warning)
            #    except:
            #        return (-1, res, e[0], '')
            done += 1
        #
        # TODO: Send a request with the result and multi-thread !
        #
        if context.get('defer_parent_store_computation'):
            self._parent_store_compute(cr)
        return (done, 0, 0, 0)

    def read(self, cr, user, ids, fields=None, context=None, load='_classic_read'):
        raise _('The read method is not implemented on this object !')

    def get_invalid_fields(self,cr,uid):
        return list(self._invalids)

    def _validate(self, cr, uid, ids, context=None):
        context = context or {}
        lng = context.get('lang', False) or 'en_US'
        trans = self.pool.get('ir.translation')
        error_msgs = []
        for constraint in self._constraints:
            fun, msg, fields = constraint
            if not fun(self, cr, uid, ids):
                translated_msg = trans._get_source(cr, uid, self._name, 'constraint', lng, source=msg) or msg
                error_msgs.append(
                        _("Error occurred while validating the field(s) %s: %s") % (','.join(fields), translated_msg)
                )
                self._invalids.update(fields)
        if error_msgs:
            cr.rollback()
            raise except_orm('ValidateError', '\n'.join(error_msgs))
        else:
            self._invalids.clear()

    def default_get(self, cr, uid, fields_list, context=None):
        return {}

    def perm_read(self, cr, user, ids, context=None, details=True):
        raise _('The perm_read method is not implemented on this object !')

    def unlink(self, cr, uid, ids, context=None):
        raise _('The unlink method is not implemented on this object !')

    def write(self, cr, user, ids, vals, context=None):
        raise _('The write method is not implemented on this object !')

    def create(self, cr, user, vals, context=None):
        raise _('The create method is not implemented on this object !')

    # returns the definition of each field in the object
    # the optional fields parameter can limit the result to some fields
    def fields_get_keys(self, cr, user, context=None, read_access=True):
        if context is None:
            context = {}
        res = self._columns.keys()
        for parent in self._inherits:
            res.extend(self.pool.get(parent).fields_get_keys(cr, user, fields, context))
        return res

    def fields_get(self, cr, user, fields=None, context=None, read_access=True):
        if context is None:
            context = {}
        res = {}
        translation_obj = self.pool.get('ir.translation')
        for parent in self._inherits:
            res.update(self.pool.get(parent).fields_get(cr, user, fields, context))

        if self._columns.keys():
            for f in self._columns.keys():
                if fields and f not in fields:
                    continue
                res[f] = {'type': self._columns[f]._type}
                for arg in ('string', 'readonly', 'states', 'size', 'required',
                        'change_default', 'translate', 'help', 'select'):
                    if getattr(self._columns[f], arg):
                        res[f][arg] = getattr(self._columns[f], arg)
                if not read_access:
                    res[f]['readonly'] = True
                    res[f]['states'] = {}
                for arg in ('digits', 'invisible','filters'):
                    if hasattr(self._columns[f], arg) \
                            and getattr(self._columns[f], arg):
                        res[f][arg] = getattr(self._columns[f], arg)

                res_trans = translation_obj._get_source(cr, user, self._name + ',' + f, 'field', context.get('lang', False) or 'en_US', self._columns[f].string)
                if res_trans:
                    res[f]['string'] = res_trans
                help_trans = translation_obj._get_source(cr, user, self._name + ',' + f, 'help', context.get('lang', False) or 'en_US')
                if help_trans:
                    res[f]['help'] = help_trans

                if hasattr(self._columns[f], 'selection'):
                    if isinstance(self._columns[f].selection, (tuple, list)):
                        sel = self._columns[f].selection
                        # translate each selection option
                        sel2 = []
                        for (key, val) in sel:
                            val2 = None
                            if val:
                                val2 = translation_obj._get_source(cr, user, self._name + ',' + f, 'selection', context.get('lang', False) or 'en_US', val)
                            sel2.append((key, val2 or val))
                        sel = sel2
                        res[f]['selection'] = sel
                    else:
                        # call the 'dynamic selection' function
                        res[f]['selection'] = self._columns[f].selection(self, cr,
                                user, context)
                if res[f]['type'] in ('one2many', 'many2many', 'many2one', 'one2one'):
                    res[f]['relation'] = self._columns[f]._obj
                    res[f]['domain'] = self._columns[f]._domain
                    res[f]['context'] = self._columns[f]._context
        else:
            #TODO : read the fields from the database
            pass

        if fields:
            # filter out fields which aren't in the fields list
            for r in res.keys():
                if r not in fields:
                    del res[r]
        return res

    #
    # Overload this method if you need a window title which depends on the context
    #
    def view_header_get(self, cr, user, view_id=None, view_type='form', context=None):
        return False

    def __view_look_dom(self, cr, user, node, view_id, context=None):
        if not context:
            context = {}
        result = False
        fields = {}
        childs = True

        if node.tag == 'field':
            if node.get('name'):
                attrs = {}
                try:
                    if node.get('name') in self._columns:
                        column = self._columns[node.get('name')]
                    else:
                        column = self._inherit_fields[node.get('name')][2]
                except:
                    column = False

                if column:
                    relation = column._obj
                    childs = False
                    views = {}
                    for f in node:
                        if f.tag in ('form', 'tree', 'graph'):
                            node.remove(f)
                            ctx = context.copy()
                            ctx['base_model_name'] = self._name
                            xarch, xfields = self.pool.get(relation).__view_look_dom_arch(cr, user, f, view_id, ctx)
                            views[str(f.tag)] = {
                                'arch': xarch,
                                'fields': xfields
                            }
                    attrs = {'views': views}
                    if node.get('widget') and node.get('widget') == 'selection':
                        # We can not use the 'string' domain has it is defined according to the record !
                        dom = None
                        if column._domain and not isinstance(column._domain, (str, unicode)):
                            dom = column._domain
                        attrs['selection'] = self.pool.get(relation).name_search(cr, user, '', dom, context=context)
                        if (node.get('required') and not int(node.get('required'))) or not column.required:
                            attrs['selection'].append((False,''))
                fields[node.get('name')] = attrs

        elif node.tag in ('form', 'tree'):
            result = self.view_header_get(cr, user, False, node.tag, context)
            if result:
                node.set('string', result)

        elif node.tag == 'calendar':
            for additional_field in ('date_start', 'date_delay', 'date_stop', 'color'):
                if node.get(additional_field):
                    fields[node.get(additional_field)] = {}

        if 'groups' in node.attrib:
            if node.get('groups'):
                groups = node.get('groups').split(',')
                readonly = False
                access_pool = self.pool.get('ir.model.access')
                for group in groups:
                    readonly = readonly or access_pool.check_groups(cr, user, group)
                if not readonly:
                    node.set('invisible', '1')
            del(node.attrib['groups'])

        # translate view
        if ('lang' in context) and not result:
            if node.get('string'):
                trans = self.pool.get('ir.translation')._get_source(cr, user, self._name, 'view', context['lang'], node.get('string').encode('utf8'))
                if not trans and ('base_model_name' in context):
                    trans = self.pool.get('ir.translation')._get_source(cr, user, context['base_model_name'], 'view', context['lang'], node.get('string').encode('utf8'))
                if trans:
                    node.set('string', trans)
            if node.get('sum'):
                trans = self.pool.get('ir.translation')._get_source(cr, user, self._name, 'view', context['lang'], node.get('sum').encode('utf8'))
                if trans:
                    node.set('sum', trans)

        if childs:
            for f in node:
                fields.update(self.__view_look_dom(cr, user, f, view_id, context))

        return fields

    def __view_look_dom_arch(self, cr, user, node, view_id, context=None):
        fields_def = self.__view_look_dom(cr, user, node, view_id, context=context)

        rolesobj = self.pool.get('res.roles')
        usersobj = self.pool.get('res.users')

        buttons = (n for n in node.getiterator('button') if n.get('type') != 'object')
        for button in buttons:
            can_click = True
            if user != 1:   # admin user has all roles
                user_roles = usersobj.read(cr, user, [user], ['roles_id'])[0]['roles_id']
                # TODO handle the case of more than one workflow for a model
                cr.execute("""SELECT DISTINCT t.role_id 
                                FROM wkf 
                          INNER JOIN wkf_activity a ON a.wkf_id = wkf.id 
                          INNER JOIN wkf_transition t ON (t.act_to = a.id)
                               WHERE wkf.osv = %s
                                 AND t.signal = %s
                           """, (self._name, button.get('name'),))
                roles = cr.fetchall()
                
                # draft -> valid = signal_next (role X)
                # draft -> cancel = signal_cancel (no role)
                #
                # valid -> running = signal_next (role Y)
                # valid -> cancel = signal_cancel (role Z)
                #
                # running -> done = signal_next (role Z)
                # running -> cancel = signal_cancel (role Z)
                # As we don't know the object state, in this scenario, 
                #   the button "signal_cancel" will be always shown as there is no restriction to cancel in draft
                #   the button "signal_next" will be show if the user has any of the roles (X Y or Z)
                # The verification will be made later in workflow process...
                if roles:
                    can_click = any((not role) or rolesobj.check(cr, user, user_roles, role) for (role,) in roles)
            
            button.set('readonly', str(int(not can_click)))

        arch = etree.tostring(node, encoding="utf-8").replace('\t', '')
        fields = self.fields_get(cr, user, fields_def.keys(), context)
        for field in fields_def:
            if field == 'id':
                # sometime, the view may containt the (invisible) field 'id' needed for a domain (when 2 objects have cross references)
                fields['id'] = {'readonly': True, 'type': 'integer', 'string': 'ID'}
            elif field in fields:
                fields[field].update(fields_def[field])
            else:
                cr.execute('select name, model from ir_ui_view where (id=%s or inherit_id=%s) and arch like %s', (view_id, view_id, '%%%s%%' % field))
                res = cr.fetchall()[:]
                model = res[0][1]
                res.insert(0, ("Can't find field '%s' in the following view parts composing the view of object model '%s':" % (field, model), None))
                msg = "\n * ".join([r[0] for r in res])
                msg += "\n\nEither you wrongly customised this view, or some modules bringing those views are not compatible with your current data model"
                netsvc.Logger().notifyChannel('orm', netsvc.LOG_ERROR, msg)
                raise except_orm('View error', msg)

        return arch, fields

    def __get_default_calendar_view(self):
        """Generate a default calendar view (For internal use only).
        """

        arch = ('<?xml version="1.0" encoding="utf-8"?>\n'
                '<calendar string="%s" date_start="%s"') % (self._description, self._date_name)

        if 'user_id' in self._columns:
            arch += ' color="user_id"'

        elif 'partner_id' in self._columns:
            arch += ' color="partner_id"'

        if 'date_stop' in self._columns:
            arch += ' date_stop="date_stop"'

        elif 'date_end' in self._columns:
            arch += ' date_stop="date_end"'

        elif 'date_delay' in self._columns:
            arch += ' date_delay="date_delay"'

        elif 'planned_hours' in self._columns:
            arch += ' date_delay="planned_hours"'

        arch += ('>\n'
                 '  <field name="%s"/>\n'
                 '</calendar>') % (self._rec_name)

        return arch

    #
    # if view_id, view_type is not required
    #
    def fields_view_get(self, cr, user, view_id=None, view_type='form', context=None, toolbar=False):
        if not context:
            context = {}

        def encode(s):
            if isinstance(s, unicode):
                return s.encode('utf8')
            return s

        def _inherit_apply(src, inherit):
            def _find(node, node2):
                if node2.tag == 'xpath':
                    res = node.xpath(node2.get('expr'))
                    if res:
                        return res[0]
                    else:
                        return None
                else:
                    for n in node.getiterator(node2.tag):
                        res = True
                        for attr in node2.attrib:
                            if attr == 'position':
                                continue
                            if n.get(attr):
                                if n.get(attr) == node2.get(attr):
                                    continue
                            res = False
                        if res:
                            return n
                return None
            # End: _find(node, node2)

            doc_dest = etree.fromstring(encode(inherit))
            toparse = [ doc_dest ]
            while len(toparse):
                node2 = toparse.pop(0)
                if node2.tag == 'data':
                    toparse += [ c for c in doc_dest ]
                    continue
                node = _find(src, node2)
                if node is not None:
                    pos = 'inside'
                    if node2.get('position'):
                        pos = node2.get('position')
                    if pos == 'replace':
                        parent = node.getparent()
                        if parent is None:
                            src = copy.deepcopy(node2[0])
                        else:
                            for child in node2:
                                node.addprevious(child)
                            node.getparent().remove(node)
                    else:
                        sib = node.getnext()
                        for child in node2:
                            if pos == 'inside':
                                node.append(child)
                            elif pos == 'after':
                                if sib is None:
                                    node.addnext(child)
                                else:
                                    sib.addprevious(child)
                            elif pos == 'before':
                                node.addprevious(child)
                            else:
                                raise AttributeError(_('Unknown position in inherited view %s !') % pos)
                else:
                    attrs = ''.join([
                        ' %s="%s"' % (attr, node2.get(attr))
                        for attr in node2.attrib
                        if attr != 'position'
                    ])
                    tag = "<%s%s>" % (node2.tag, attrs)
                    raise AttributeError(_("Couldn't find tag '%s' in parent view !") % tag)
            return src
        # End: _inherit_apply(src, inherit)

        result = {'type': view_type, 'model': self._name}

        ok = True
        model = True
        sql_res = False
        while ok:
            view_ref = context.get(view_type + '_view_ref', False)
            if view_ref:
                if '.' in view_ref:
                    module, view_ref = view_ref.split('.', 1)
                    cr.execute("SELECT res_id FROM ir_model_data WHERE model='ir.ui.view' AND module=%s AND name=%s", (module, view_ref))
                    view_ref_res = cr.fetchone()
                    if view_ref_res:
                        view_id = view_ref_res[0]

            if view_id:
                query = "SELECT arch,name,field_parent,id,type,inherit_id FROM ir_ui_view WHERE id=%s"
                params = (view_id,)
                if model:
                    query += " AND model=%s"
                    params += (self._name,)
                cr.execute(query, params)
            else:
                cr.execute('''SELECT
                        arch,name,field_parent,id,type,inherit_id
                    FROM
                        ir_ui_view
                    WHERE
                        model=%s AND
                        type=%s AND
                        inherit_id IS NULL
                    ORDER BY priority''', (self._name, view_type))
            sql_res = cr.fetchone()
            if not sql_res:
                break
            ok = sql_res[5]
            view_id = ok or sql_res[3]
            model = False

        # if a view was found
        if sql_res:
            result['type'] = sql_res[4]
            result['view_id'] = sql_res[3]
            result['arch'] = sql_res[0]

            def _inherit_apply_rec(result, inherit_id):
                # get all views which inherit from (ie modify) this view
                cr.execute('select arch,id from ir_ui_view where inherit_id=%s and model=%s order by priority', (inherit_id, self._name))
                sql_inherit = cr.fetchall()
                for (inherit, id) in sql_inherit:
                    result = _inherit_apply(result, inherit)
                    result = _inherit_apply_rec(result, id)
                return result

            inherit_result = etree.fromstring(encode(result['arch']))
            result['arch'] = _inherit_apply_rec(inherit_result, sql_res[3])

            result['name'] = sql_res[1]
            result['field_parent'] = sql_res[2] or False
        else:
            # otherwise, build some kind of default view
            if view_type == 'form':
                res = self.fields_get(cr, user, context=context)
                xml = '''<?xml version="1.0" encoding="utf-8"?>''' \
                '''<form string="%s">''' % (self._description,)
                for x in res:
                    if res[x]['type'] not in ('one2many', 'many2many'):
                        xml += '<field name="%s"/>' % (x,)
                        if res[x]['type'] == 'text':
                            xml += "<newline/>"
                xml += "</form>"
            elif view_type == 'tree':
                _rec_name = self._rec_name
                if _rec_name not in self._columns:
                    _rec_name = self._columns.keys()[0]
                xml = '''<?xml version="1.0" encoding="utf-8"?>''' \
                '''<tree string="%s"><field name="%s"/></tree>''' \
                % (self._description, self._rec_name)
            elif view_type == 'calendar':
                xml = self.__get_default_calendar_view()
            else:
                xml = ''
            result['arch'] = etree.fromstring(encode(xml))
            result['name'] = 'default'
            result['field_parent'] = False
            result['view_id'] = 0

        xarch, xfields = self.__view_look_dom_arch(cr, user, result['arch'], view_id, context=context)
        result['arch'] = xarch
        result['fields'] = xfields
        if toolbar:
            def clean(x):
                x = x[2]
                for key in ('report_sxw_content', 'report_rml_content',
                        'report_sxw', 'report_rml',
                        'report_sxw_content_data', 'report_rml_content_data'):
                    if key in x:
                        del x[key]
                return x
            ir_values_obj = self.pool.get('ir.values')
            resprint = ir_values_obj.get(cr, user, 'action',
                    'client_print_multi', [(self._name, False)], False,
                    context)
            resaction = ir_values_obj.get(cr, user, 'action',
                    'client_action_multi', [(self._name, False)], False,
                    context)

            resrelate = ir_values_obj.get(cr, user, 'action',
                    'client_action_relate', [(self._name, False)], False,
                    context)
            resprint = map(clean, resprint)
            resaction = map(clean, resaction)
            resaction = filter(lambda x: not x.get('multi', False), resaction)
            resprint = filter(lambda x: not x.get('multi', False), resprint)
            resrelate = map(lambda x: x[2], resrelate)

            for x in resprint+resaction+resrelate:
                x['string'] = x['name']

            result['toolbar'] = {
                'print': resprint,
                'action': resaction,
                'relate': resrelate
            }
        return result

    _view_look_dom_arch = __view_look_dom_arch

    def search_count(self, cr, user, args, context=None):
        if not context:
            context = {}
        res = self.search(cr, user, args, context=context, count=True)
        if isinstance(res, list):
            return len(res)
        return res

    def search(self, cr, user, args, offset=0, limit=None, order=None,
            context=None, count=False):
        raise _('The search method is not implemented on this object !')

    def name_get(self, cr, user, ids, context=None):
        raise _('The name_get method is not implemented on this object !')

    def name_search(self, cr, user, name='', args=None, operator='ilike', context=None, limit=80):
        raise _('The name_search method is not implemented on this object !')

    def copy(self, cr, uid, id, default=None, context=None):
        raise _('The copy method is not implemented on this object !')

    def exists(self, cr, uid, id, context=None):
        raise _('The exists method is not implemented on this object !')

    def read_string(self, cr, uid, id, langs, fields=None, context=None):
        res = {}
        res2 = {}
        self.pool.get('ir.model.access').check(cr, uid, 'ir.translation', 'read', context=context)
        if not fields:
            fields = self._columns.keys() + self._inherit_fields.keys()
        for lang in langs:
            res[lang] = {'code': lang}
            for f in fields:
                if f in self._columns:
                    res_trans = self.pool.get('ir.translation')._get_source(cr, uid, self._name+','+f, 'field', lang)
                    if res_trans:
                        res[lang][f] = res_trans
                    else:
                        res[lang][f] = self._columns[f].string
        for table in self._inherits:
            cols = intersect(self._inherit_fields.keys(), fields)
            res2 = self.pool.get(table).read_string(cr, uid, id, langs, cols, context)
        for lang in res2:
            if lang in res:
                res[lang]['code'] = lang
            for f in res2[lang]:
                res[lang][f] = res2[lang][f]
        return res

    def write_string(self, cr, uid, id, langs, vals, context=None):
        self.pool.get('ir.model.access').check(cr, uid, 'ir.translation', 'write', context=context)
        for lang in langs:
            for field in vals:
                if field in self._columns:
                    src = self._columns[field].string
                    self.pool.get('ir.translation')._set_ids(cr, uid, self._name+','+field, 'field', lang, [0], vals[field], src)
        for table in self._inherits:
            cols = intersect(self._inherit_fields.keys(), vals)
            if cols:
                self.pool.get(table).write_string(cr, uid, id, langs, vals, context)
        return True

    def _check_removed_columns(self, cr, log=False):
        raise NotImplementedError()

class orm_memory(orm_template):
    _protected = ['read', 'write', 'create', 'default_get', 'perm_read', 'unlink', 'fields_get', 'fields_view_get', 'search', 'name_get', 'distinct_field_get', 'name_search', 'copy', 'import_data', 'search_count', 'exists']
    _inherit_fields = {}
    _max_count = 200
    _max_hours = 1
    _check_time = 20

    def __init__(self, cr):
        super(orm_memory, self).__init__(cr)
        self.datas = {}
        self.next_id = 0
        self.check_id = 0
        cr.execute('delete from wkf_instance where res_type=%s', (self._name,))

    def vaccum(self, cr, uid):
        self.check_id += 1
        if self.check_id % self._check_time:
            return True
        tounlink = []
        max = time.time() - self._max_hours * 60 * 60
        for id in self.datas:
            if self.datas[id]['internal.date_access'] < max:
                tounlink.append(id)
        self.unlink(cr, uid, tounlink)
        if len(self.datas)>self._max_count:
            sorted = map(lambda x: (x[1]['internal.date_access'], x[0]), self.datas.items())
            sorted.sort()
            ids = map(lambda x: x[1], sorted[:len(self.datas)-self._max_count])
            self.unlink(cr, uid, ids)
        return True

    def read(self, cr, user, ids, fields_to_read=None, context=None, load='_classic_read'):
        if not context:
            context = {}
        if not fields_to_read:
            fields_to_read = self._columns.keys()
        result = []
        if self.datas:
            if isinstance(ids, (int, long)):
                ids = [ids]
            for id in ids:
                r = {'id': id}
                for f in fields_to_read:
                    if id in self.datas:
                        r[f] = self.datas[id].get(f, False)
                        if r[f] and isinstance(self._columns[f], fields.binary) and context.get('bin_size', False):
                            r[f] = len(r[f])
                result.append(r)
                if id in self.datas:
                    self.datas[id]['internal.date_access'] = time.time()
            fields_post = filter(lambda x: x in self._columns and not getattr(self._columns[x], load), fields_to_read)
            for f in fields_post:
                res2 = self._columns[f].get_memory(cr, self, ids, f, user, context=context, values=result)
                for record in result:
                    record[f] = res2[record['id']]
            if isinstance(ids, (int, long)):
                return result[0]
        return result

    def write(self, cr, user, ids, vals, context=None):
        if not ids:
            return True
        vals2 = {}
        upd_todo = []
        for field in vals:
            if self._columns[field]._classic_write:
                vals2[field] = vals[field]
            else:
                upd_todo.append(field)
        for id_new in ids:
            self.datas[id_new].update(vals2)
            self.datas[id_new]['internal.date_access'] = time.time()
            for field in upd_todo:
                self._columns[field].set_memory(cr, self, id_new, field, vals[field], user, context)
        self._validate(cr, user, [id_new], context)
        wf_service = netsvc.LocalService("workflow")
        wf_service.trg_write(user, self._name, id_new, cr)
        return id_new

    def create(self, cr, user, vals, context=None):
        self.vaccum(cr, user)
        self.next_id += 1
        id_new = self.next_id
        default = []
        for f in self._columns.keys():
            if not f in vals:
                default.append(f)
        if len(default):
            vals.update(self.default_get(cr, user, default, context))
        vals2 = {}
        upd_todo = []
        for field in vals:
            if self._columns[field]._classic_write:
                vals2[field] = vals[field]
            else:
                upd_todo.append(field)
        self.datas[id_new] = vals2
        self.datas[id_new]['internal.date_access'] = time.time()

        for field in upd_todo:
            self._columns[field].set_memory(cr, self, id_new, field, vals[field], user, context)
        self._validate(cr, user, [id_new], context)
        wf_service = netsvc.LocalService("workflow")
        wf_service.trg_create(user, self._name, id_new, cr)
        return id_new

    def default_get(self, cr, uid, fields_list, context=None):
        if not context:
            context = {}
        value = {}
        # get the default values for the inherited fields
        for f in fields_list:
            if f in self._defaults:
                value[f] = self._defaults[f](self, cr, uid, context)
            fld_def = ((f in self._columns) and self._columns[f]) \
                    or ((f in self._inherit_fields) and self._inherit_fields[f][2]) \
                    or False

        # get the default values set by the user and override the default
        # values defined in the object
        ir_values_obj = self.pool.get('ir.values')
        res = ir_values_obj.get(cr, uid, 'default', False, [self._name])
        for id, field, field_value in res:
            if field in fields_list:
                fld_def = (field in self._columns) and self._columns[field] or self._inherit_fields[field][2]
                if fld_def._type in ('many2one', 'one2one'):
                    obj = self.pool.get(fld_def._obj)
                    if not obj.search(cr, uid, [('id', '=', field_value)]):
                        continue
                if fld_def._type in ('many2many'):
                    obj = self.pool.get(fld_def._obj)
                    field_value2 = []
                    for i in range(len(field_value)):
                        if not obj.search(cr, uid, [('id', '=',
                            field_value[i])]):
                            continue
                        field_value2.append(field_value[i])
                    field_value = field_value2
                if fld_def._type in ('one2many'):
                    obj = self.pool.get(fld_def._obj)
                    field_value2 = []
                    for i in range(len(field_value)):
                        field_value2.append({})
                        for field2 in field_value[i]:
                            if obj._columns[field2]._type in ('many2one', 'one2one'):
                                obj2 = self.pool.get(obj._columns[field2]._obj)
                                if not obj2.search(cr, uid,
                                        [('id', '=', field_value[i][field2])]):
                                    continue
                            # TODO add test for many2many and one2many
                            field_value2[i][field2] = field_value[i][field2]
                    field_value = field_value2
                value[field] = field_value

        # get the default values from the context
        for key in context or {}:
            if key.startswith('default_') and (key[8:] in fields_list):
                value[key[8:]] = context[key]
        return value

    def search(self, cr, user, args, offset=0, limit=None, order=None,
            context=None, count=False):
        return self.datas.keys()

    def unlink(self, cr, uid, ids, context=None):
        for id in ids:
            if id in self.datas:
                del self.datas[id]
        if ids:
            cr.execute('delete from wkf_instance where res_type=%s and res_id in %s', (self._name, tuple(ids)))
        return True

    def perm_read(self, cr, user, ids, context=None, details=True):
        result = []
        for id in ids:
            result.append({
                'create_uid': (user, 'Root'),
                'create_date': time.strftime('%Y-%m-%d %H:%M:%S'),
                'write_uid': False,
                'write_date': False,
                'id': id
            })
        return result

    def _check_removed_columns(self, cr, log=False):
        # nothing to check in memory...
        pass
    
    def exists(self, cr, uid, id, context=None):
        return id in self.datas

class orm(orm_template):
    _sql_constraints = []
    _table = None
    _protected = ['read','write','create','default_get','perm_read','unlink','fields_get','fields_view_get','search','name_get','distinct_field_get','name_search','copy','import_data','search_count', 'exists']

    def _parent_store_compute(self, cr):
        if not self._parent_store:
            return
        logger = netsvc.Logger()
        logger.notifyChannel('orm', netsvc.LOG_INFO, 'Computing parent left and right for table %s...' % (self._table, ))
        def browse_rec(root, pos=0):
# TODO: set order
            where = self._parent_name+'='+str(root)
            if not root:
                where = self._parent_name+' IS NULL'
            if self._parent_order:
                where += ' order by '+self._parent_order
            cr.execute('SELECT id FROM '+self._table+' WHERE '+where)
            pos2 = pos + 1
            childs = cr.fetchall()
            for id in childs:
                pos2 = browse_rec(id[0], pos2)
            cr.execute('update '+self._table+' set parent_left=%s, parent_right=%s where id=%s', (pos,pos2,root))
            return pos2+1
        query = 'SELECT id FROM '+self._table+' WHERE '+self._parent_name+' IS NULL'
        if self._parent_order:
            query += ' order by '+self._parent_order
        pos = 0
        cr.execute(query)
        for (root,) in cr.fetchall():
            pos = browse_rec(root, pos)
        return True

    def _update_store(self, cr, f, k):
        logger = netsvc.Logger()
        logger.notifyChannel('orm', netsvc.LOG_INFO, "storing computed values of fields.function '%s'" % (k,))
        ss = self._columns[k]._symbol_set
        update_query = 'UPDATE "%s" SET "%s"=%s WHERE id=%%s' % (self._table, k, ss[0])
        cr.execute('select id from '+self._table)
        ids_lst = map(lambda x: x[0], cr.fetchall())
        while ids_lst:
            iids = ids_lst[:40]
            ids_lst = ids_lst[40:]
            res = f.get(cr, self, iids, k, 1, {})
            for key,val in res.items():
                if f._multi:
                    val = val[k]
                # if val is a many2one, just write the ID
                if type(val)==tuple:
                    val = val[0]
                if (val<>False) or (type(val)<>bool):
                    cr.execute(update_query, (ss[1](val), key))

    def _check_removed_columns(self, cr, log=False):
        logger = netsvc.Logger()
        # iterate on the database columns to drop the NOT NULL constraints
        # of fields which were required but have been removed (or will be added by another module)
        columns = [c for c in self._columns if not (isinstance(self._columns[c], fields.function) and not self._columns[c].store)]
        columns += ('id', 'write_uid', 'write_date', 'create_uid', 'create_date') # openerp access columns
        cr.execute("SELECT a.attname, a.attnotnull"
                   "  FROM pg_class c, pg_attribute a"
                   " WHERE c.relname=%s"
                   "   AND c.oid=a.attrelid"
                   "   AND a.attisdropped=%s"
                   "   AND pg_catalog.format_type(a.atttypid, a.atttypmod) NOT IN ('cid', 'tid', 'oid', 'xid')"
                   "   AND a.attname NOT IN %s",
                       (self._table, False, tuple(columns)))
        for column in cr.dictfetchall():
            if log:
                logger.notifyChannel("orm", netsvc.LOG_DEBUG, "column %s is in the table %s but not in the corresponding object %s" % (column['attname'], self._table, self._name))
            if column['attnotnull']:
                cr.execute('ALTER TABLE "%s" ALTER COLUMN "%s" DROP NOT NULL' % (self._table, column['attname']))

    def _auto_init(self, cr, context={}):
        store_compute =  False
        logger = netsvc.Logger()
        create = False
        todo_end = []
        self._field_create(cr, context=context)
        if not hasattr(self, "_auto") or self._auto:
            cr.execute("SELECT relname FROM pg_class WHERE relkind in ('r','v') AND relname=%s", (self._table,))
            if not cr.rowcount:
                cr.execute('CREATE TABLE "%s" (id SERIAL NOT NULL, PRIMARY KEY(id)) WITH OIDS' % (self._table,))
                create = True
            cr.commit()
            if self._parent_store:
                cr.execute("""SELECT c.relname
                    FROM pg_class c, pg_attribute a
                    WHERE c.relname=%s AND a.attname=%s AND c.oid=a.attrelid
                    """, (self._table, 'parent_left'))
                if not cr.rowcount:
                    if 'parent_left' not in self._columns:
                        logger.notifyChannel('orm', netsvc.LOG_ERROR, 'create a column parent_left on object %s: fields.integer(\'Left Parent\', select=1)' % (self._table, ))
                    if 'parent_right' not in self._columns:
                        logger.notifyChannel('orm', netsvc.LOG_ERROR, 'create a column parent_right on object %s: fields.integer(\'Right Parent\', select=1)' % (self._table, ))
                    if self._columns[self._parent_name].ondelete != 'cascade':
                        logger.notifyChannel('orm', netsvc.LOG_ERROR, "The column %s on object %s must be set as ondelete='cascade'" % (self._parent_name, self._name))
                    cr.execute('ALTER TABLE "%s" ADD COLUMN "parent_left" INTEGER' % (self._table,))
                    cr.execute('ALTER TABLE "%s" ADD COLUMN "parent_right" INTEGER' % (self._table,))
                    cr.commit()
                    store_compute = True

            if self._log_access:
                logs = {
                    'create_uid': 'INTEGER REFERENCES res_users ON DELETE SET NULL',
                    'create_date': 'TIMESTAMP',
                    'write_uid': 'INTEGER REFERENCES res_users ON DELETE SET NULL',
                    'write_date': 'TIMESTAMP'
                }
                for k in logs:
                    cr.execute("""
                        SELECT c.relname
                          FROM pg_class c, pg_attribute a
                         WHERE c.relname=%s AND a.attname=%s AND c.oid=a.attrelid
                        """, (self._table, k))
                    if not cr.rowcount:
                        cr.execute('ALTER TABLE "%s" ADD COLUMN "%s" %s' % (self._table, k, logs[k]))
                        cr.commit()

            self._check_removed_columns(cr, log=False)

            # iterate on the "object columns"
            todo_update_store = []
            update_custom_fields = context.get('update_custom_fields', False)
            for k in self._columns:
                if k in ('id', 'write_uid', 'write_date', 'create_uid', 'create_date'):
                    continue
                    #raise _('Can not define a column %s. Reserved keyword !') % (k,)
                #Not Updating Custom fields
                if k.startswith('x_') and not update_custom_fields:
                    continue
                f = self._columns[k]

                if isinstance(f, fields.one2many):
                    cr.execute("SELECT relname FROM pg_class WHERE relkind='r' AND relname=%s", (f._obj,))
                    
                    if self.pool.get(f._obj):
                        if f._fields_id not in self.pool.get(f._obj)._columns.keys():
                            if not self.pool.get(f._obj)._inherits or (f._fields_id not in self.pool.get(f._obj)._inherit_fields.keys()):
                                raise except_orm('Programming Error', ("There is no reference field '%s' found for '%s'") % (f._fields_id,f._obj,))
                    
                    if cr.fetchone():
                        cr.execute("SELECT count(1) as c FROM pg_class c,pg_attribute a WHERE c.relname=%s AND a.attname=%s AND c.oid=a.attrelid", (f._obj, f._fields_id))
                        res = cr.fetchone()[0]
                        if not res:
                            cr.execute('ALTER TABLE "%s" ADD FOREIGN KEY (%s) REFERENCES "%s" ON DELETE SET NULL' % (self._obj, f._fields_id, f._table))
                elif isinstance(f, fields.many2many):
                    cr.execute("SELECT relname FROM pg_class WHERE relkind in ('r','v') AND relname=%s", (f._rel,))
                    if not cr.dictfetchall():
                        if not self.pool.get(f._obj):
                            raise except_orm('Programming Error', ('There is no reference available for %s') % (f._obj,))
                        ref = self.pool.get(f._obj)._table
#                        ref = f._obj.replace('.', '_')
                        cr.execute('CREATE TABLE "%s" ("%s" INTEGER NOT NULL REFERENCES "%s" ON DELETE CASCADE, "%s" INTEGER NOT NULL REFERENCES "%s" ON DELETE CASCADE) WITH OIDS' % (f._rel, f._id1, self._table, f._id2, ref))
                        cr.execute('CREATE INDEX "%s_%s_index" ON "%s" ("%s")' % (f._rel, f._id1, f._rel, f._id1))
                        cr.execute('CREATE INDEX "%s_%s_index" ON "%s" ("%s")' % (f._rel, f._id2, f._rel, f._id2))
                        cr.commit()
                else:
                    cr.execute("SELECT c.relname,a.attname,a.attlen,a.atttypmod,a.attnotnull,a.atthasdef,t.typname,CASE WHEN a.attlen=-1 THEN a.atttypmod-4 ELSE a.attlen END as size " \
                               "FROM pg_class c,pg_attribute a,pg_type t " \
                               "WHERE c.relname=%s " \
                               "AND a.attname=%s " \
                               "AND c.oid=a.attrelid " \
                               "AND a.atttypid=t.oid", (self._table, k))
                    res = cr.dictfetchall()
                    if not res:
                        if not isinstance(f, fields.function) or f.store:

                            # add the missing field
                            cr.execute('ALTER TABLE "%s" ADD COLUMN "%s" %s' % (self._table, k, get_pg_type(f)[1]))

                            # initialize it
                            if not create and k in self._defaults:
                                default = self._defaults[k](self, cr, 1, {})
                                ss = self._columns[k]._symbol_set
                                query = 'UPDATE "%s" SET "%s"=%s' % (self._table, k, ss[0])
                                cr.execute(query, (ss[1](default),))
                                cr.commit()
                                logger.notifyChannel('orm', netsvc.LOG_DEBUG, 'setting default value of new column %s of table %s'% (k, self._table))
                            elif not create:
                                logger.notifyChannel('orm', netsvc.LOG_DEBUG, 'creating new column %s of table %s'% (k, self._table))

                            if isinstance(f, fields.function):
                                order = 10
                                if f.store is not True:
                                    order = f.store[f.store.keys()[0]][2]
                                todo_update_store.append((order, f,k))

                            # and add constraints if needed
                            if isinstance(f, fields.many2one):
                                if not self.pool.get(f._obj):
                                    raise except_orm('Programming Error', ('There is no reference available for %s') % (f._obj,))
                                ref = self.pool.get(f._obj)._table
#                                ref = f._obj.replace('.', '_')
                                # ir_actions is inherited so foreign key doesn't work on it
                                if ref != 'ir_actions':
                                    cr.execute('ALTER TABLE "%s" ADD FOREIGN KEY ("%s") REFERENCES "%s" ON DELETE %s' % (self._table, k, ref, f.ondelete))
                            if f.select:
                                cr.execute('CREATE INDEX "%s_%s_index" ON "%s" ("%s")' % (self._table, k, self._table, k))
                            if f.required:
                                try:
                                    cr.commit()
                                    cr.execute('ALTER TABLE "%s" ALTER COLUMN "%s" SET NOT NULL' % (self._table, k))
                                except Exception:
                                    logger.notifyChannel('orm', netsvc.LOG_WARNING, 'WARNING: unable to set column %s of table %s not null !\nTry to re-run: openerp-server.py --update=module\nIf it doesn\'t work, update records and execute manually:\nALTER TABLE %s ALTER COLUMN %s SET NOT NULL' % (k, self._table, self._table, k))
                            cr.commit()
                    elif len(res)==1:
                        f_pg_def = res[0]
                        f_pg_type = f_pg_def['typname']
                        f_pg_size = f_pg_def['size']
                        f_pg_notnull = f_pg_def['attnotnull']
                        if isinstance(f, fields.function) and not f.store:
                            logger.notifyChannel('orm', netsvc.LOG_INFO, 'column %s (%s) in table %s removed: converted to a function !\n' % (k, f.string, self._table))
                            cr.execute('ALTER TABLE "%s" DROP COLUMN "%s" CASCADE'% (self._table, k))
                            cr.commit()
                            f_obj_type = None
                        else:
                            f_obj_type = get_pg_type(f) and get_pg_type(f)[0]

                        if f_obj_type:
                            ok = False
                            casts = [
                                ('text', 'char', 'VARCHAR(%d)' % (f.size or 0,), '::VARCHAR(%d)'%(f.size or 0,)),
                                ('varchar', 'text', 'TEXT', ''),
                                ('int4', 'float', get_pg_type(f)[1], '::'+get_pg_type(f)[1]),
                                ('date', 'datetime', 'TIMESTAMP', '::TIMESTAMP'),
                                ('numeric', 'float', get_pg_type(f)[1], '::'+get_pg_type(f)[1]),
                                ('float8', 'float', get_pg_type(f)[1], '::'+get_pg_type(f)[1]),
                            ]
                            # !!! Avoid reduction of varchar field !!!
                            if f_pg_type == 'varchar' and f._type == 'char' and f_pg_size < f.size:
                            # if f_pg_type == 'varchar' and f._type == 'char' and f_pg_size != f.size:
                                logger.notifyChannel('orm', netsvc.LOG_INFO, "column '%s' in table '%s' changed size" % (k, self._table))
                                cr.execute('ALTER TABLE "%s" RENAME COLUMN "%s" TO temp_change_size' % (self._table, k))
                                cr.execute('ALTER TABLE "%s" ADD COLUMN "%s" VARCHAR(%d)' % (self._table, k, f.size))
                                cr.execute('UPDATE "%s" SET "%s"=temp_change_size::VARCHAR(%d)' % (self._table, k, f.size))
                                cr.execute('ALTER TABLE "%s" DROP COLUMN temp_change_size CASCADE' % (self._table,))
                                cr.commit()
                            for c in casts:
                                if (f_pg_type==c[0]) and (f._type==c[1]):
                                    # Adding upcoming 6 lines to check whether only the size of the fields got changed or not.E.g. :(16,3) to (16,4)
                                    field_size_change = False
                                    if f_pg_type in ['int4','numeric','float8']:
                                        if f.digits:
                                            field_size = (65535 * f.digits[0]) + f.digits[0] + f.digits[1]
                                            if field_size != f_pg_size:
                                                field_size_change = True
                                                
                                    if f_pg_type != f_obj_type or field_size_change:
                                        if f_pg_type != f_obj_type:
                                            logger.notifyChannel('orm', netsvc.LOG_INFO, "column '%s' in table '%s' changed type to %s." % (k, self._table, c[1]))
                                        if field_size_change:
                                            logger.notifyChannel('orm', netsvc.LOG_INFO, "column '%s' in table '%s' changed in the size." % (k, self._table))
                                        ok = True
                                        cr.execute('ALTER TABLE "%s" RENAME COLUMN "%s" TO temp_change_size' % (self._table, k))
                                        cr.execute('ALTER TABLE "%s" ADD COLUMN "%s" %s' % (self._table, k, c[2]))
                                        cr.execute(('UPDATE "%s" SET "%s"=temp_change_size'+c[3]) % (self._table, k))
                                        cr.execute('ALTER TABLE "%s" DROP COLUMN temp_change_size CASCADE' % (self._table,))
                                        cr.commit()
                                    break

                            if f_pg_type != f_obj_type:
                                if not ok:
                                    logger.notifyChannel('orm', netsvc.LOG_WARNING, "column '%s' in table '%s' has changed type (DB = %s, def = %s) but unable to migrate this change !" % (k, self._table, f_pg_type, f._type))

                            # if the field is required and hasn't got a NOT NULL constraint
                            if f.required and f_pg_notnull == 0:
                                # set the field to the default value if any
                                if k in self._defaults:
                                    default = self._defaults[k](self, cr, 1, {})
                                    if (default is not None):
                                        ss = self._columns[k]._symbol_set
                                        query = 'UPDATE "%s" SET "%s"=%s WHERE "%s" is NULL' % (self._table, k, ss[0], k)
                                        cr.execute(query, (ss[1](default),))
                                # add the NOT NULL constraint
                                cr.commit()
                                try:
                                    cr.execute('ALTER TABLE "%s" ALTER COLUMN "%s" SET NOT NULL' % (self._table, k))
                                    cr.commit()
                                except Exception:
                                    logger.notifyChannel('orm', netsvc.LOG_WARNING, 'unable to set a NOT NULL constraint on column %s of the %s table !\nIf you want to have it, you should update the records and execute manually:\nALTER TABLE %s ALTER COLUMN %s SET NOT NULL' % (k, self._table, self._table, k))
                                cr.commit()
                            elif not f.required and f_pg_notnull == 1:
                                cr.execute('ALTER TABLE "%s" ALTER COLUMN "%s" DROP NOT NULL' % (self._table, k))
                                cr.commit()
                            indexname = '%s_%s_index' % (self._table, k)
                            cr.execute("SELECT indexname FROM pg_indexes WHERE indexname = %s and tablename = %s", (indexname, self._table))
                            res = cr.dictfetchall()
                            if not res and f.select:
                                cr.execute('CREATE INDEX "%s_%s_index" ON "%s" ("%s")' % (self._table, k, self._table, k))
                                cr.commit()
                            if res and not f.select:
                                cr.execute('DROP INDEX "%s_%s_index"' % (self._table, k))
                                cr.commit()
                            if isinstance(f, fields.many2one):
                                ref = self.pool.get(f._obj)._table
                                if ref != 'ir_actions':
                                    cr.execute('SELECT confdeltype, conname FROM pg_constraint as con, pg_class as cl1, pg_class as cl2, '
                                                'pg_attribute as att1, pg_attribute as att2 '
                                            'WHERE con.conrelid = cl1.oid '
                                                'AND cl1.relname = %s '
                                                'AND con.confrelid = cl2.oid '
                                                'AND cl2.relname = %s '
                                                'AND array_lower(con.conkey, 1) = 1 '
                                                'AND con.conkey[1] = att1.attnum '
                                                'AND att1.attrelid = cl1.oid '
                                                'AND att1.attname = %s '
                                                'AND array_lower(con.confkey, 1) = 1 '
                                                'AND con.confkey[1] = att2.attnum '
                                                'AND att2.attrelid = cl2.oid '
                                                'AND att2.attname = %s '
                                                "AND con.contype = 'f'", (self._table, ref, k, 'id'))
                                    res = cr.dictfetchall()
                                    if res:
                                        confdeltype = {
                                            'RESTRICT': 'r',
                                            'NO ACTION': 'a',
                                            'CASCADE': 'c',
                                            'SET NULL': 'n',
                                            'SET DEFAULT': 'd',
                                        }
                                        if res[0]['confdeltype'] != confdeltype.get(f.ondelete.upper(), 'a'):
                                            cr.execute('ALTER TABLE "' + self._table + '" DROP CONSTRAINT "' + res[0]['conname'] + '"')
                                            cr.execute('ALTER TABLE "' + self._table + '" ADD FOREIGN KEY ("' + k + '") REFERENCES "' + ref + '" ON DELETE ' + f.ondelete)
                                            cr.commit()
                    else:
                        logger.notifyChannel('orm', netsvc.LOG_ERROR, "Programming error !")
            for order,f,k in todo_update_store:
                todo_end.append((order, self._update_store, (f, k)))

        else:
            cr.execute("SELECT relname FROM pg_class WHERE relkind in ('r','v') AND relname=%s", (self._table,))
            create = not bool(cr.fetchone())

        cr.commit()     # start a new transaction

        for (key, con, _) in self._sql_constraints:
            conname = '%s_%s' % (self._table, key)
            cr.execute("SELECT conname FROM pg_constraint where conname=%s", (conname,))
            if not cr.dictfetchall():
                query = 'ALTER TABLE "%s" ADD CONSTRAINT "%s" %s' % (self._table, conname, con,)
                try:
                    cr.execute(query)
                    cr.commit()
                except:
                    logger.notifyChannel('orm', netsvc.LOG_WARNING, 'unable to add \'%s\' constraint on table %s !\n If you want to have it, you should update the records and execute manually:\n%s' % (con, self._table, query))
                    cr.rollback()

        if create:
            if hasattr(self, "_sql"):
                for line in self._sql.split(';'):
                    line2 = line.replace('\n', '').strip()
                    if line2:
                        cr.execute(line2)
                        cr.commit()
        if store_compute:
            self._parent_store_compute(cr)
            cr.commit()
        return todo_end

    def __init__(self, cr):
        super(orm, self).__init__(cr)

        if not hasattr(self, '_log_access'):
            # if not access is not specify, it is the same value as _auto
            self._log_access = not hasattr(self, "_auto") or self._auto

        self._columns = self._columns.copy()
        for store_field in self._columns:
            f = self._columns[store_field]
            if not isinstance(f, fields.function):
                continue
            if not f.store:
                continue
            if self._columns[store_field].store is True:
                sm = {self._name:(lambda self,cr, uid, ids, c={}: ids, None, 10)}
            else:
                sm = self._columns[store_field].store
            for object, aa in sm.items():
                if len(aa)==3:
                    (fnct,fields2,order)=aa
                else:
                    raise except_orm('Error',
                        ('Invalid function definition %s in object %s !\nYou must use the definition: store={object:(fnct, fields, priority)}.' % (store_field, self._name)))
                self.pool._store_function.setdefault(object, [])
                ok = True
                for x,y,z,e,f in self.pool._store_function[object]:
                    if (x==self._name) and (y==store_field) and (e==fields2):
                        if f==order:
                            ok = False
                if ok:
                    self.pool._store_function[object].append( (self._name, store_field, fnct, fields2, order))
                    self.pool._store_function[object].sort(lambda x,y: cmp(x[4],y[4]))

        for (key, _, msg) in self._sql_constraints:
            self.pool._sql_error[self._table+'_'+key] = msg

        # Load manual fields

        cr.execute("SELECT id FROM ir_model_fields WHERE name=%s AND model=%s", ('state', 'ir.model.fields'))
        if cr.fetchone():
            cr.execute('SELECT * FROM ir_model_fields WHERE model=%s AND state=%s', (self._name, 'manual'))
            for field in cr.dictfetchall():
                if field['name'] in self._columns:
                    continue
                attrs = {
                    'string': field['field_description'],
                    'required': bool(field['required']),
                    'readonly': bool(field['readonly']),
                    'domain': field['domain'] or None,
                    'size': field['size'],
                    'ondelete': field['on_delete'],
                    'translate': (field['translate']),
                    #'select': int(field['select_level'])
                }

                if field['ttype'] == 'selection':
                    self._columns[field['name']] = getattr(fields, field['ttype'])(eval(field['selection']), **attrs)
                elif field['ttype'] == 'reference':
                    self._columns[field['name']] = getattr(fields, field['ttype'])(selection=eval(field['selection']), **attrs)
                elif field['ttype'] == 'many2one':
                    self._columns[field['name']] = getattr(fields, field['ttype'])(field['relation'], **attrs)
                elif field['ttype'] == 'one2many':
                    self._columns[field['name']] = getattr(fields, field['ttype'])(field['relation'], field['relation_field'], **attrs)
                elif field['ttype'] == 'many2many':
                    _rel1 = field['relation'].replace('.', '_')
                    _rel2 = field['model'].replace('.', '_')
                    _rel_name = 'x_%s_%s_%s_rel' %(_rel1, _rel2, field['name'])
                    self._columns[field['name']] = getattr(fields, field['ttype'])(field['relation'], _rel_name, 'id1', 'id2', **attrs)
                else:
                    self._columns[field['name']] = getattr(fields, field['ttype'])(**attrs)

        self._inherits_reload()
        if not self._sequence:
            self._sequence = self._table+'_id_seq'
        for k in self._defaults:
            assert (k in self._columns) or (k in self._inherit_fields), 'Default function defined in %s but field %s does not exist !' % (self._name, k,)
        for f in self._columns:
            self._columns[f].restart()

    def default_get(self, cr, uid, fields_list, context=None):
        if not context:
            context = {}
        value = {}
        # get the default values for the inherited fields
        for t in self._inherits.keys():
            value.update(self.pool.get(t).default_get(cr, uid, fields_list,
                context))

        # get the default values defined in the object
        for f in fields_list:
            if f in self._defaults:
                value[f] = self._defaults[f](self, cr, uid, context)
            fld_def = ((f in self._columns) and self._columns[f]) \
                    or ((f in self._inherit_fields) and self._inherit_fields[f][2]) \
                    or False
            if isinstance(fld_def, fields.property):
                property_obj = self.pool.get('ir.property')
                definition_id = fld_def._field_get(cr, uid, self._name, f)
                nid = property_obj.search(cr, uid, [('fields_id', '=',
                    definition_id), ('res_id', '=', False)])
                if nid:
                    prop_value = property_obj.browse(cr, uid, nid[0],
                            context=context).value
                    value[f] = (prop_value and int(prop_value.split(',')[1])) \
                            or False

        # get the default values set by the user and override the default
        # values defined in the object
        ir_values_obj = self.pool.get('ir.values')
        res = ir_values_obj.get(cr, uid, 'default', False, [self._name])
        for id, field, field_value in res:
            if field in fields_list:
                fld_def = (field in self._columns) and self._columns[field] or self._inherit_fields[field][2]
                if fld_def._type in ('many2one', 'one2one'):
                    obj = self.pool.get(fld_def._obj)
                    if not obj.search(cr, uid, [('id', '=', field_value or False)]):
                        continue
                if fld_def._type in ('many2many'):
                    obj = self.pool.get(fld_def._obj)
                    field_value2 = []
                    for i in range(len(field_value)):
                        if not obj.search(cr, uid, [('id', '=',
                            field_value[i])]):
                            continue
                        field_value2.append(field_value[i])
                    field_value = field_value2
                if fld_def._type in ('one2many'):
                    obj = self.pool.get(fld_def._obj)
                    field_value2 = []
                    for i in range(len(field_value)):
                        field_value2.append({})
                        for field2 in field_value[i]:
                            if field2 in obj._columns.keys() and obj._columns[field2]._type in ('many2one', 'one2one'):
                                obj2 = self.pool.get(obj._columns[field2]._obj)
                                if not obj2.search(cr, uid,
                                        [('id', '=', field_value[i][field2])]):
                                    continue
                            elif field2 in obj._inherit_fields.keys() and obj._inherit_fields[field2][2]._type in ('many2one', 'one2one'):
                                obj2 = self.pool.get(obj._inherit_fields[field2][2]._obj)
                                if not obj2.search(cr, uid,
                                        [('id', '=', field_value[i][field2])]):
                                    continue
                            # TODO add test for many2many and one2many
                            field_value2[i][field2] = field_value[i][field2]
                    field_value = field_value2
                value[field] = field_value
        for key in context or {}:
            if key.startswith('default_') and (key[8:] in fields_list):
                value[key[8:]] = context[key]
        return value

    #
    # Update objects that uses this one to update their _inherits fields
    #
    def _inherits_reload_src(self):
        for obj in self.pool.obj_pool.values():
            if self._name in obj._inherits:
                obj._inherits_reload()

    def _inherits_reload(self):
        res = {}
        for table in self._inherits:
            res.update(self.pool.get(table)._inherit_fields)
            for col in self.pool.get(table)._columns.keys():
                res[col] = (table, self._inherits[table], self.pool.get(table)._columns[col])
            for col in self.pool.get(table)._inherit_fields.keys():
                res[col] = (table, self._inherits[table], self.pool.get(table)._inherit_fields[col][2])
        self._inherit_fields = res
        self._inherits_reload_src()

    def fields_get(self, cr, user, fields=None, context=None):
        ira = self.pool.get('ir.model.access')
        read_access = ira.check(cr, user, self._name, 'write', raise_exception=False, context=context) or \
                      ira.check(cr, user, self._name, 'create', raise_exception=False, context=context)
        return super(orm, self).fields_get(cr, user, fields, context, read_access)

    def read(self, cr, user, ids, fields=None, context=None, load='_classic_read'):
        if not context:
            context = {}
        self.pool.get('ir.model.access').check(cr, user, self._name, 'read', context=context)
        if not fields:
            fields = self._columns.keys() + self._inherit_fields.keys()
        select = ids
        if isinstance(ids, (int, long)):
            select = [ids]
        result = self._read_flat(cr, user, select, fields, context, load)

        for r in result:
            for key, v in r.items():
                if v is None:
                    r[key] = False
                if key in self._columns.keys():
                    type = self._columns[key]._type
                elif key in self._inherit_fields.keys():
                    type = self._inherit_fields[key][2]._type
                else:
                    continue
                if type == 'reference' and v:
                    model,ref_id = v.split(',')
                    table = self.pool.get(model)._table
                    cr.execute('select id from "%s" where id=%%s' % (table,), (ref_id,))
                    id_exist = cr.fetchone()
                    if not id_exist:
                        query = 'UPDATE "%s" SET "%s"=NULL WHERE "%s"=%%s' % (self._table, key, key)
                        cr.execute(query, (v,))
                        r[key] = ''

        if isinstance(ids, (int, long)):
            return result and result[0] or False
        return result

    def _read_flat(self, cr, user, ids, fields_to_read, context=None, load='_classic_read'):
        if not context:
            context = {}
        if not ids:
            return []

        if fields_to_read == None:
            fields_to_read = self._columns.keys()

        # construct a clause for the rules :
        d1, d2 = self.pool.get('ir.rule').domain_get(cr, user, self._name)

        # all inherited fields + all non inherited fields for which the attribute whose name is in load is True
        fields_pre = [f for f in fields_to_read if
                           f == self.CONCURRENCY_CHECK_FIELD
                        or (f in self._columns and getattr(self._columns[f], '_classic_write'))
                     ] + self._inherits.values()

        res = []
        if len(fields_pre):
            def convert_field(f):
                if f in ('create_date', 'write_date'):
                    return "date_trunc('second', %s) as %s" % (f, f)
                if f == self.CONCURRENCY_CHECK_FIELD:
                    if self._log_access:
                        return "COALESCE(write_date, create_date, now())::timestamp AS %s" % (f,)
                    return "now()::timestamp AS %s" % (f,)
                if isinstance(self._columns[f], fields.binary) and context.get('bin_size', False):
                    return 'length("%s") as "%s"' % (f, f)
                return '"%s"' % (f,)
            fields_pre2 = map(convert_field, fields_pre)
            order_by = self._parent_order or self._order

            select_fields = ','.join(fields_pre2 + ['id'])
            query = 'SELECT %s FROM "%s" WHERE id in %%s' % (select_fields, self._table)
            if d1:
                query += " AND " + d1
            query += " ORDER BY " + order_by

            for i in range(0, len(ids), cr.IN_MAX):
                sub_ids = ids[i:i+cr.IN_MAX]
                if d1:
                    cr.execute(query, (tuple(sub_ids),) + d2)
                    if cr.rowcount != len(set(sub_ids)):
                        raise except_orm(_('AccessError'),
                                _('You try to bypass an access rule (Document type: %s).') % self._description)
                else:
                    cr.execute(query, (tuple(sub_ids),))
                res.extend(cr.dictfetchall())
        else:
            res = map(lambda x: {'id': x}, ids)

        for f in fields_pre:
            if f == self.CONCURRENCY_CHECK_FIELD:
                continue
            if self._columns[f].translate:
                ids = map(lambda x: x['id'], res)
                res_trans = self.pool.get('ir.translation')._get_ids(cr, user, self._name+','+f, 'model', context.get('lang', False) or 'en_US', ids)
                for r in res:
                    r[f] = res_trans.get(r['id'], False) or r[f]

        for table in self._inherits:
            col = self._inherits[table]
            cols = intersect(self._inherit_fields.keys(), fields_to_read)
            if not cols:
                continue
            res2 = self.pool.get(table).read(cr, user, [x[col] for x in res], cols, context, load)

            res3 = {}
            for r in res2:
                res3[r['id']] = r
                del r['id']

            for record in res:
                if not record[col]:# if the record is deleted from _inherits table?
                    continue
                record.update(res3[record[col]])
                if col not in fields_to_read:
                    del record[col]

        # all fields which need to be post-processed by a simple function (symbol_get)
        fields_post = filter(lambda x: x in self._columns and self._columns[x]._symbol_get, fields_to_read)
        if fields_post:
            # maybe it would be faster to iterate on the fields then on res, so that we wouldn't need
            # to get the _symbol_get in each occurence
            for r in res:
                for f in fields_post:
                    r[f] = self._columns[f]._symbol_get(r[f])
        ids = map(lambda x: x['id'], res)

        # all non inherited fields for which the attribute whose name is in load is False
        fields_post = filter(lambda x: x in self._columns and not getattr(self._columns[x], load), fields_to_read)

        # Compute POST fields
        todo = {}
        for f in fields_post:
            todo.setdefault(self._columns[f]._multi, [])
            todo[self._columns[f]._multi].append(f)
        for key,val in todo.items():
            if key:
                res2 = self._columns[val[0]].get(cr, self, ids, val, user, context=context, values=res)
                for pos in val:
                    for record in res:
                        record[pos] = res2[record['id']][pos]
            else:
                for f in val:
                    res2 = self._columns[f].get(cr, self, ids, f, user, context=context, values=res)
                    for record in res:
                        record[f] = res2[record['id']]

#for f in fields_post:
#    # get the value of that field for all records/ids
#    res2 = self._columns[f].get(cr, self, ids, f, user, context=context, values=res)
#    for record in res:
#        record[f] = res2[record['id']]

        readonly = None
        for vals in res:
            for field in vals.copy():
                fobj = None
                if field in self._columns:
                    fobj = self._columns[field]

                if not fobj:
                    continue
                groups = fobj.read
                if groups:
                    edit = False
                    for group in groups:
                        module = group.split(".")[0]
                        grp = group.split(".")[1]
                        cr.execute("select count(*) from res_groups_users_rel where gid in (select res_id from ir_model_data where name=%s and module=%s and model=%s) and uid=%s", \
                                   (grp, module, 'res.groups', user))
                        readonly = cr.fetchall()
                        if readonly[0][0] >= 1:
                            edit = True
                            break
                        elif readonly[0][0] == 0:
                            edit = False
                        else:
                            edit = False

                    if not edit:
                        if type(vals[field]) == type([]):
                            vals[field] = []
                        elif type(vals[field]) == type(0.0):
                            vals[field] = 0
                        elif type(vals[field]) == type(''):
                            vals[field] = '=No Permission='
                        else:
                            vals[field] = False
        return res

    def perm_read(self, cr, user, ids, context=None, details=True):
        if not context:
            context = {}
        if not ids:
            return []
        uniq = isinstance(ids, (int, long))
        if uniq:
            ids = [ids]

        fields = 'id'
        if self._log_access:
            fields += ', create_uid, create_date, write_uid, write_date'
        query = 'SELECT %s FROM "%s" WHERE id in %%s' % (fields, self._table)
        cr.execute(query, (tuple(ids),))
        res = cr.dictfetchall()
        for r in res:
            for key in r:
                r[key] = r[key] or False
                if key in ('write_uid', 'create_uid', 'uid') and details:
                    if r[key]:
                        r[key] = self.pool.get('res.users').name_get(cr, user, [r[key]])[0]
        if uniq:
            return res[ids[0]]
        return res

    def _check_concurrency(self, cr, ids, context):
        if not context:
            return
        if context.get(self.CONCURRENCY_CHECK_FIELD) and self._log_access:
            def key(oid):
                return "%s,%s" % (self._name, oid)
            santa = "(id = %s AND %s < COALESCE(write_date, create_date, now())::timestamp)"
            for i in range(0, len(ids), cr.IN_MAX):
                sub_ids = tools.flatten(((oid, context[self.CONCURRENCY_CHECK_FIELD][key(oid)])
                                          for oid in ids[i:i+cr.IN_MAX]
                                          if key(oid) in context[self.CONCURRENCY_CHECK_FIELD]))
                if sub_ids:
                    cr.execute("SELECT count(1) FROM %s WHERE %s" % (self._table, " OR ".join([santa]*(len(sub_ids)/2))), sub_ids)
                    res = cr.fetchone()
                    if res and res[0]:
                        raise except_orm('ConcurrencyException', _('Records were modified in the meanwhile'))

    def unlink(self, cr, uid, ids, context=None):
        if not ids:
            return True
        if isinstance(ids, (int, long)):
            ids = [ids]

        result_store = self._store_get_values(cr, uid, ids, None, context)

        self._check_concurrency(cr, ids, context)

        self.pool.get('ir.model.access').check(cr, uid, self._name, 'unlink', context=context)

        properties = self.pool.get('ir.property')
        domain = [('res_id', '=', False), 
                  ('value', 'in', ['%s,%s' % (self._name, i) for i in ids]), 
                 ]
        if properties.search(cr, uid, domain, context=context):
            raise except_orm(_('Error'), _('Unable to delete this document because it is used as a default property'))

        wf_service = netsvc.LocalService("workflow")
        for oid in ids:
            wf_service.trg_delete(uid, self._name, oid, cr)

        d1, d2 = self.pool.get('ir.rule').domain_get(cr, uid, self._name)

        from_where = ' FROM "%s" WHERE id IN %%s' % (self._table,)
        if d1:
            from_where += ' AND ' + d1

        for i in range(0, len(ids), cr.IN_MAX):
            sub_ids = ids[i:i+cr.IN_MAX]
            if d1:
                cr.execute('SELECT id' + from_where, (tuple(sub_ids),) + d2)
                if not cr.rowcount == len(set(sub_ids)):
                    raise except_orm(_('AccessError'),
                            _('You try to bypass an access rule (Document type: %s).') % \
                                    self._description)

                cr.execute('DELETE' + from_where, (tuple(sub_ids),) + d2)
            else:
                cr.execute('DELETE' + from_where, (tuple(sub_ids),))

        for order, object, store_ids, fields in result_store:
            if object != self._name:
                obj = self.pool.get(object)
                cr.execute('select id from '+obj._table+' where id in %s', (tuple(store_ids),))
                rids = map(lambda x: x[0], cr.fetchall())
                if rids:
                    obj._store_set_values(cr, uid, rids, fields, context)
        return True

    #
    # TODO: Validate
    #
    def write(self, cr, user, ids, vals, context=None):
        readonly = None
        for field in vals.copy():
            fobj = None
            if field in self._columns:
                fobj = self._columns[field]
            else:
                fobj = self._inherit_fields[field][2]
            if not fobj:
                continue
            groups = fobj.write

            if groups:
                edit = False
                for group in groups:
                    module = group.split(".")[0]
                    grp = group.split(".")[1]
                    cr.execute("select count(*) from res_groups_users_rel where gid in (select res_id from ir_model_data where name=%s and module=%s and model=%s) and uid=%s", \
                               (grp, module, 'res.groups', user))
                    readonly = cr.fetchall()
                    if readonly[0][0] >= 1:
                        edit = True
                        break
                    elif readonly[0][0] == 0:
                        edit = False
                    else:
                        edit = False

                if not edit:
                    vals.pop(field)


        if not context:
            context = {}
        if not ids:
            return True
        if isinstance(ids, (int, long)):
            ids = [ids]

        self._check_concurrency(cr, ids, context)

        self.pool.get('ir.model.access').check(cr, user, self._name, 'write', context=context)

        # No direct update of parent_left/right
        vals.pop('parent_left', None)
        vals.pop('parent_right', None)

        parents_changed = []
        if self._parent_store and (self._parent_name in vals):
            # The parent_left/right computation may take up to
            # 5 seconds. No need to recompute the values if the
            # parent is the same. Get the current value of the parent
            base_query = 'SELECT id FROM "%s" WHERE id IN %%s AND %s' % \
                            (self._table, self._parent_name)
            params = (tuple(ids),)
            parent_val = vals[self._parent_name]
            if parent_val:
                cr.execute(base_query + " != %s", params + (parent_val,))
            else:
                cr.execute(base_query + " IS NULL", params)
            parents_changed = map(operator.itemgetter(0), cr.fetchall())

        upd0 = []
        upd1 = []
        upd_todo = []
        updend = []
        direct = []
        totranslate = context.get('lang', False) and (context['lang'] != 'en_US')
        for field in vals:
            if field in self._columns:
                if self._columns[field]._classic_write and not (hasattr(self._columns[field], '_fnct_inv')):
                    if (not totranslate) or not self._columns[field].translate:
                        upd0.append('"'+field+'"='+self._columns[field]._symbol_set[0])
                        upd1.append(self._columns[field]._symbol_set[1](vals[field]))
                    direct.append(field)
                else:
                    upd_todo.append(field)
            else:
                updend.append(field)
            if field in self._columns \
                    and hasattr(self._columns[field], 'selection') \
                    and vals[field]:
                if self._columns[field]._type == 'reference':
                    val = vals[field].split(',')[0]
                else:
                    val = vals[field]
                if isinstance(self._columns[field].selection, (tuple, list)):
                    if val not in dict(self._columns[field].selection):
                        raise except_orm(_('ValidateError'),
                        _('The value "%s" for the field "%s" is not in the selection') \
                                % (vals[field], field))
                else:
                    if val not in dict(self._columns[field].selection(
                        self, cr, user, context=context)):
                        raise except_orm(_('ValidateError'),
                        _('The value "%s" for the field "%s" is not in the selection') \
                                % (vals[field], field))

        if self._log_access:
            upd0.append('write_uid=%s')
            upd0.append('write_date=now()')
            upd1.append(user)

        if upd0:

            clause = " WHERE id IN %s"
            d1, d2 = self.pool.get('ir.rule').domain_get(cr, user, self._name)
            if d1:
                clause += ' AND ' + d1

            select_query = 'SELECT id FROM "%s" %s' % (self._table, clause)
            update_query = 'UPDATE "%s" SET %s %s' % (self._table, ','.join(upd0), clause)

            for i in range(0, len(ids), cr.IN_MAX):
                sub_ids = set(ids[i:i+cr.IN_MAX])
                if d1:
                    cr.execute(select_query, (tuple(sub_ids),) + d2)
                    if cr.rowcount != len(sub_ids):
                        raise except_orm(_('AccessError'),
                                _('You try to bypass an access rule (Document type: %s).') % \
                                        self._description)

                    cr.execute(update_query, upd1 + (tuple(sub_ids),) + d2)
                else:
                    cr.execute(select_query, (tuple(sub_ids),))
                    if cr.rowcount != len(sub_ids):
                        raise except_orm(_('AccessError'),
                                _('You try to write on an record that doesn\'t exist ' \
                                        '(Document type: %s).') % self._description)

                    cr.execute(update_query, upd1 + [tuple(sub_ids)])

            if totranslate:
                for f in direct:
                    if self._columns[f].translate:
                        src_trans = self.pool.get(self._name).read(cr,user,ids,[f])[0][f]
                        if not src_trans:
                            src_trans = vals[f]
                            # Inserting value to DB
                            self.write(cr, user, ids, {f:vals[f]})
                        self.pool.get('ir.translation')._set_ids(cr, user, self._name+','+f, 'model', context['lang'], ids, vals[f], src_trans)


        # call the 'set' method of fields which are not classic_write
        upd_todo.sort(lambda x, y: self._columns[x].priority-self._columns[y].priority)

        # default element in context must be removed when call a one2many or many2many
        rel_context = context.copy()
        for c in context.items():
            if c[0].startswith('default_'):
                del rel_context[c[0]]

        result = []
        for field in upd_todo:
            for id in ids:
                result += self._columns[field].set(cr, self, id, field, vals[field], user, context=rel_context) or []

        for table in self._inherits:
            col = self._inherits[table]
            query = 'SELECT DISTINCT "%s" FROM "%s" WHERE id IN %%s' % (col, self._table)
            nids = []
            for i in range(0, len(ids), cr.IN_MAX):
                sub_ids = ids[i:i+cr.IN_MAX]
                cr.execute(query, (tuple(sub_ids),))
                nids.extend([x[0] for x in cr.fetchall()])

            v = {}
            for val in updend:
                if self._inherit_fields[val][0] == table:
                    v[val] = vals[val]
            self.pool.get(table).write(cr, user, nids, v, context)

        self._validate(cr, user, ids, context)

        # TODO: use _order to set dest at the right position and not first node of parent
        # We can't defer parent_store computation because the stored function
        # fields that are computer may refer (directly or indirectly) to
        # parent_left/right (via a child_of domain)
        if parents_changed:
            if self.pool._init:
                self.pool._init_parent[self._name]=True
            else:
                order = self._parent_order or self._order
                parent_val = vals[self._parent_name]
                if parent_val:
                    clause, params = '%s=%%s' % (self._parent_name,), (parent_val,)
                else:
                    clause, params = '%s IS NULL' % (self._parent_name,), ()
                cr.execute('SELECT parent_right, id FROM "%s" WHERE %s ORDER BY %s' % (self._table, clause, order), params)
                parents = cr.fetchall()

                for id in parents_changed:
                    cr.execute('SELECT parent_left, parent_right FROM "%s" WHERE id=%%s' % (self._table,), (id,))
                    pleft, pright = cr.fetchone()
                    distance = pright - pleft + 1

                    # Find Position of the element
                    position = None
                    for (parent_pright, parent_id) in parents:
                        if parent_id == id:
                            break
                        position = parent_pright+1

                    # It's the first node of the parent
                    if not position:
                        if not parent_val:
                            position = 1
                        else:
                            cr.execute('select parent_left from '+self._table+' where id=%s', (parent_val,))
                            position = cr.fetchone()[0]+1

                    if pleft < position <= pright:
                        raise except_orm(_('UserError'), _('Recursivity Detected.'))

                    if pleft < position:
                        cr.execute('update '+self._table+' set parent_left=parent_left+%s where parent_left>=%s', (distance, position))
                        cr.execute('update '+self._table+' set parent_right=parent_right+%s where parent_right>=%s', (distance, position))
                        cr.execute('update '+self._table+' set parent_left=parent_left+%s, parent_right=parent_right+%s where parent_left>=%s and parent_left<%s', (position-pleft,position-pleft, pleft, pright))
                    else:
                        cr.execute('update '+self._table+' set parent_left=parent_left+%s where parent_left>=%s', (distance, position))
                        cr.execute('update '+self._table+' set parent_right=parent_right+%s where parent_right>=%s', (distance, position))
                        cr.execute('update '+self._table+' set parent_left=parent_left-%s, parent_right=parent_right-%s where parent_left>=%s and parent_left<%s', (pleft-position+distance,pleft-position+distance, pleft+distance, pright+distance))

        result += self._store_get_values(cr, user, ids, vals.keys(), context)
        for order, object, ids, fields in result:
            self.pool.get(object)._store_set_values(cr, user, ids, fields, context)

        wf_service = netsvc.LocalService("workflow")
        for id in ids:
            wf_service.trg_write(user, self._name, id, cr)
        return True

    #
    # TODO: Should set perm to user.xxx
    #
    def create(self, cr, user, vals, context=None):
        """ create(cr, user, vals, context) -> int
        cr = database cursor
        user = user id
        vals = dictionary of the form {'field_name':field_value, ...}
        """
        if not context:
            context = {}
        self.pool.get('ir.model.access').check(cr, user, self._name, 'create', context=context)

        default = []

        avoid_table = []
        for (t, c) in self._inherits.items():
            if c in vals:
                avoid_table.append(t)
        for f in self._columns.keys():
            if (not f in vals) and (not isinstance(self._columns[f], fields.property)):
                default.append(f)

        for f in self._inherit_fields.keys():
            if (not f in vals) and (self._inherit_fields[f][0] not in avoid_table) and (not isinstance(self._inherit_fields[f][2], fields.property)):
                default.append(f)

        if len(default):
            default_values = self.default_get(cr, user, default, context)
            for dv in default_values:
                if dv in self._columns and self._columns[dv]._type == 'many2many':
                    if default_values[dv] and isinstance(default_values[dv][0], (int, long)):
                        default_values[dv] = [(6, 0, default_values[dv])]
            vals.update(default_values)

        tocreate = {}
        for v in self._inherits:
            if self._inherits[v] not in vals:
                tocreate[v] = {}

        (upd0, upd1, upd2) = ('', '', [])
        upd_todo = []

        for v in vals.keys():
            if v in self._inherit_fields:
                (table, col, col_detail) = self._inherit_fields[v]
                tocreate[table][v] = vals[v]
                del vals[v]

        # Try-except added to filter the creation of those records whose filds are readonly.
        # Example : any dashboard which has all the fields readonly.(due to Views(database views))
        try:
            cr.execute("SELECT nextval('"+self._sequence+"')")
        except:
            raise except_orm(_('UserError'),
                        _('You cannot perform this operation.'))

        id_new = cr.fetchone()[0]
        for table in tocreate:
            id = self.pool.get(table).create(cr, user, tocreate[table])
            upd0 += ','+self._inherits[table]
            upd1 += ',%s'
            upd2.append(id)
        
        #Start : Set bool fields to be False if they are not touched(to make search more powerful) 
        bool_fields = [x for x in self._columns.keys() if self._columns[x]._type=='boolean']
        
        for bool_field in bool_fields:
            if bool_field not in vals:
                vals[bool_field] = False
        #End
        
        for field in vals:
            if field in self._columns:
                if self._columns[field]._classic_write:
                    upd0 = upd0 + ',"' + field + '"'
                    upd1 = upd1 + ',' + self._columns[field]._symbol_set[0]
                    upd2.append(self._columns[field]._symbol_set[1](vals[field]))
                else:
                    upd_todo.append(field)
            if field in self._columns \
                    and hasattr(self._columns[field], 'selection') \
                    and vals[field]:
                if self._columns[field]._type == 'reference':
                    val = vals[field].split(',')[0]
                else:
                    val = vals[field]
                if isinstance(self._columns[field].selection, (tuple, list)):
                    if val not in dict(self._columns[field].selection):
                        raise except_orm(_('ValidateError'),
                        _('The value "%s" for the field "%s" is not in the selection') \
                                % (vals[field], field))
                else:
                    if val not in dict(self._columns[field].selection(
                        self, cr, user, context=context)):
                        raise except_orm(_('ValidateError'),
                        _('The value "%s" for the field "%s" is not in the selection') \
                                % (vals[field], field))
        if self._log_access:
            upd0 += ',create_uid,create_date'
            upd1 += ',%s,now()'
            upd2.append(user)
        cr.execute('insert into "'+self._table+'" (id'+upd0+") values ("+str(id_new)+upd1+')', tuple(upd2))
        upd_todo.sort(lambda x, y: self._columns[x].priority-self._columns[y].priority)

        if self._parent_store and not context.get('defer_parent_store_computation'):
            if self.pool._init:
                self.pool._init_parent[self._name]=True
            else:
                parent = vals.get(self._parent_name, False)
                if parent:
                    cr.execute('select parent_right from '+self._table+' where '+self._parent_name+'=%s order by '+(self._parent_order or self._order), (parent,))
                    pleft_old = None
                    result_p = cr.fetchall()
                    for (pleft,) in result_p:
                        if not pleft:
                            break
                        pleft_old = pleft
                    if not pleft_old:
                        cr.execute('select parent_left from '+self._table+' where id=%s', (parent,))
                        pleft_old = cr.fetchone()[0]
                    pleft = pleft_old
                else:
                    cr.execute('select max(parent_right) from '+self._table)
                    pleft = cr.fetchone()[0] or 0
                cr.execute('update '+self._table+' set parent_left=parent_left+2 where parent_left>%s', (pleft,))
                cr.execute('update '+self._table+' set parent_right=parent_right+2 where parent_right>%s', (pleft,))
                cr.execute('update '+self._table+' set parent_left=%s,parent_right=%s where id=%s', (pleft+1,pleft+2,id_new))
                
        # default element in context must be removed when call a one2many or many2many
        rel_context = context.copy()
        for c in context.items():
            if c[0].startswith('default_'):
                del rel_context[c[0]]
        
        result = []
        for field in upd_todo:
            result += self._columns[field].set(cr, self, id_new, field, vals[field], user, rel_context) or []
        self._validate(cr, user, [id_new], context)

        if not context.get('no_store_function', False):
            result += self._store_get_values(cr, user, [id_new], vals.keys(), context)
            result.sort()
            done = []
            for order, object, ids, fields2 in result:
                if not (object, ids, fields2) in done:
                    self.pool.get(object)._store_set_values(cr, user, ids, fields2, context)
                    done.append((object, ids, fields2))

        wf_service = netsvc.LocalService("workflow")
        wf_service.trg_create(user, self._name, id_new, cr)
        return id_new

    def _store_get_values(self, cr, uid, ids, fields, context):
        result = {}
        fncts = self.pool._store_function.get(self._name, [])
        for fnct in range(len(fncts)):
            if fncts[fnct][3]:
                ok = False
                if not fields:
                    ok = True
                for f in (fields or []):
                    if f in fncts[fnct][3]:
                        ok = True
                        break
                if not ok:
                    continue

            result.setdefault(fncts[fnct][0], {})
            ids2 = fncts[fnct][2](self,cr, uid, ids, context)
            for id in filter(None, ids2):
                result[fncts[fnct][0]].setdefault(id, [])
                result[fncts[fnct][0]][id].append(fnct)
        dict = {}
        for object in result:
            k2 = {}
            for id,fnct in result[object].items():
                k2.setdefault(tuple(fnct), [])
                k2[tuple(fnct)].append(id)
            for fnct,id in k2.items():
                dict.setdefault(fncts[fnct[0]][4],[])
                dict[fncts[fnct[0]][4]].append((fncts[fnct[0]][4],object,id,map(lambda x: fncts[x][1], fnct)))
        result2 = []
        tmp = dict.keys()
        tmp.sort()
        for k in tmp:
            result2+=dict[k]
        return result2

    def _store_set_values(self, cr, uid, ids, fields, context):
        todo = {}
        keys = []
        for f in fields:
            if self._columns[f]._multi not in keys:
                keys.append(self._columns[f]._multi)
            todo.setdefault(self._columns[f]._multi, [])
            todo[self._columns[f]._multi].append(f)
        for key in keys:
            val = todo[key]
            if key:
                result = self._columns[val[0]].get(cr, self, ids, val, uid, context=context)
                for id,value in result.items():
                    upd0 = []
                    upd1 = []
                    for v in value:
                        if v not in val:
                            continue
                        if self._columns[v]._type in ('many2one', 'one2one'):
                            try:
                                value[v] = value[v][0]
                            except:
                                pass
                        upd0.append('"'+v+'"='+self._columns[v]._symbol_set[0])
                        upd1.append(self._columns[v]._symbol_set[1](value[v]))
                    upd1.append(id)
                    cr.execute('update "' + self._table + '" set ' + \
                        string.join(upd0, ',') + ' where id = %s', upd1)

            else:
                for f in val:
                    result = self._columns[f].get(cr, self, ids, f, uid, context=context)
                    for id,value in result.items():
                        if self._columns[f]._type in ('many2one', 'one2one'):
                            try:
                                value = value[0]
                            except:
                                pass
                        cr.execute('update "' + self._table + '" set ' + \
                            '"'+f+'"='+self._columns[f]._symbol_set[0] + ' where id = %s', (self._columns[f]._symbol_set[1](value),id))
        return True

    #
    # TODO: Validate
    #
    def perm_write(self, cr, user, ids, fields, context=None):
        raise _('This method does not exist anymore')

    # TODO: ameliorer avec NULL
    def _where_calc(self, cr, user, args, active_test=True, context=None):
        if not context:
            context = {}
        args = args[:]
        # if the object has a field named 'active', filter out all inactive
        # records unless they were explicitely asked for
        if 'active' in self._columns and (active_test and context.get('active_test', True)):
            if args:
                active_in_args = False
                for a in args:
                    if a[0] == 'active':
                        active_in_args = True
                if not active_in_args:
                    args.insert(0, ('active', '=', 1))
            else:
                args = [('active', '=', 1)]

        if args:
            import expression
            e = expression.expression(args)
            e.parse(cr, user, self, context)
            tables = e.get_tables()
            qu1, qu2 = e.to_sql()
            qu1 = qu1 and [qu1] or []
        else:
            qu1, qu2, tables = [], [], ['"%s"' % self._table]

        return (qu1, qu2, tables)

    def _check_qorder(self, word):
        if not regex_order.match(word):
            raise except_orm(_('AccessError'), _('Bad query.'))
        return True

    def search(self, cr, user, args, offset=0, limit=None, order=None,
            context=None, count=False):
        if not context:
            context = {}
        # compute the where, order by, limit and offset clauses
        (qu1, qu2, tables) = self._where_calc(cr, user, args, context=context)

        if len(qu1):
            qu1 = ' where '+string.join(qu1, ' and ')
        else:
            qu1 = ''

        if order:
            self._check_qorder(order)
        order_by = order or self._order

        limit_str = limit and ' limit %d' % limit or ''
        offset_str = offset and ' offset %d' % offset or ''


        # construct a clause for the rules :
        d1, d2 = self.pool.get('ir.rule').domain_get(cr, user, self._name)
        if d1:
            qu1 = qu1 and qu1+' and '+d1 or ' where '+d1
            qu2 += d2

        if count:
            cr.execute('select count(%s.id) from ' % self._table +
                    ','.join(tables) +qu1 + limit_str + offset_str, qu2)
            res = cr.fetchall()
            return res[0][0]
        # execute the "main" query to fetch the ids we were searching for
        cr.execute('select %s.id from ' % self._table + ','.join(tables) +qu1+' order by '+order_by+limit_str+offset_str, qu2)
        res = cr.fetchall()
        return [x[0] for x in res]

    # returns the different values ever entered for one field
    # this is used, for example, in the client when the user hits enter on
    # a char field
    def distinct_field_get(self, cr, uid, field, value, args=None, offset=0, limit=None):
        if not args:
            args = []
        if field in self._inherit_fields:
            return self.pool.get(self._inherit_fields[field][0]).distinct_field_get(cr, uid, field, value, args, offset, limit)
        else:
            return self._columns[field].search(cr, self, args, field, value, offset, limit, uid)

    def name_get(self, cr, user, ids, context=None):
        if not context:
            context = {}
        if not ids:
            return []
        if isinstance(ids, (int, long)):
            ids = [ids]
        return [(r['id'], tools.ustr(r[self._rec_name])) for r in self.read(cr, user, ids,
            [self._rec_name], context, load='_classic_write')]

    def name_search(self, cr, user, name='', args=None, operator='ilike', context=None, limit=80):
        if not args:
            args = []
        if not context:
            context = {}
        args = args[:]
        if name:
            args += [(self._rec_name, operator, name)]
        ids = self.search(cr, user, args, limit=limit, context=context)
        res = self.name_get(cr, user, ids, context)
        return res

    def copy_data(self, cr, uid, id, default=None, context=None):
        if not context:
            context = {}
        if not default:
            default = {}
        if 'state' not in default:
            if 'state' in self._defaults:
                default['state'] = self._defaults['state'](self, cr, uid, context)
        data = self.read(cr, uid, [id], context=context)[0]
        fields = self.fields_get(cr, uid, context=context)
        trans_data=[]
        for f in fields:
            ftype = fields[f]['type']

            if self._log_access and f in ('create_date', 'create_uid', 'write_date', 'write_uid'):
                del data[f]

            if f in default:
                data[f] = default[f]
            elif ftype == 'function':
                del data[f]
            elif ftype == 'many2one':
                try:
                    data[f] = data[f] and data[f][0]
                except:
                    pass
            elif ftype in ('one2many', 'one2one'):
                res = []
                rel = self.pool.get(fields[f]['relation'])
                for rel_id in data[f]:
                    # the lines are first duplicated using the wrong (old)
                    # parent but then are reassigned to the correct one thanks
                    # to the (4, ...)
                    d,t = rel.copy_data(cr, uid, rel_id, context=context)
                    res.append((0, 0, d))
                    trans_data += t
                data[f] = res
            elif ftype == 'many2many':
                data[f] = [(6, 0, data[f])]

        trans_obj = self.pool.get('ir.translation')
        trans_name=''
        for f in fields:
            trans_flag=True
            if f in self._columns and self._columns[f].translate:
                trans_name=self._name+","+f
            elif f in self._inherit_fields and self._inherit_fields[f][2].translate:
                trans_name=self._inherit_fields[f][0]+","+f
            else:
                trans_flag=False

            if trans_flag:
                trans_ids = trans_obj.search(cr, uid, [
                        ('name', '=', trans_name),
                        ('res_id','=',data['id'])
                    ])

                trans_data.extend(trans_obj.read(cr,uid,trans_ids,context=context))

        del data['id']

        for v in self._inherits:
            del data[self._inherits[v]]
        return data, trans_data

    def copy(self, cr, uid, id, default=None, context=None):
        trans_obj = self.pool.get('ir.translation')
        data, trans_data = self.copy_data(cr, uid, id, default, context)
        new_id = self.create(cr, uid, data, context)
        for record in trans_data:
            del record['id']
            record['res_id'] = new_id
            trans_obj.create(cr, uid, record, context)
        return new_id

    def exists(self, cr, uid, id, context=None):
        cr.execute('SELECT count(1) FROM "%s" where id=%%s' % (self._table,), (id,))
        return bool(cr.fetchone()[0])

    def check_recursion(self, cr, uid, ids, parent=None):
        if not parent:
            parent = self._parent_name
        ids_parent = ids[:]
        query = 'SELECT distinct "%s" FROM "%s" WHERE id IN %%s' % (parent, self._table)
        while ids_parent:
            ids_parent2 = []
            for i in range(0, len(ids), cr.IN_MAX):
                sub_ids_parent = ids_parent[i:i+cr.IN_MAX]
                cr.execute(query, (tuple(sub_ids_parent),))
                ids_parent2.extend(filter(None, map(lambda x: x[0], cr.fetchall())))
            ids_parent = ids_parent2
            for i in ids_parent:
                if i in ids:
                    return False
        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
