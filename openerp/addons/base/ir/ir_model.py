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
import logging
import re
import time
from operator import itemgetter

from osv import fields,osv
import ir
import netsvc
from osv.orm import except_orm, browse_record
import tools
from tools.safe_eval import safe_eval as eval
from tools import config
from tools.translate import _
import pooler

def _get_fields_type(self, cr, uid, context=None):
    cr.execute('select distinct ttype,ttype from ir_model_fields')
    field_types = cr.fetchall()
    field_types_copy = field_types
    for types in field_types_copy:
        if not hasattr(fields,types[0]):
            field_types.remove(types)
    return field_types

def _in_modules(self, cr, uid, ids, field_name, arg, context=None):
    #pseudo-method used by fields.function in ir.model/ir.model.fields
    module_pool = self.pool.get("ir.module.module")
    installed_module_ids = module_pool.search(cr, uid, [('state','=','installed')])
    installed_module_names = module_pool.read(cr, uid, installed_module_ids, ['name'], context=context)
    installed_modules = set(x['name'] for x in installed_module_names)

    result = {}
    xml_ids = osv.osv._get_xml_ids(self, cr, uid, ids)
    for k,v in xml_ids.iteritems():
        result[k] = ', '.join(sorted(installed_modules & set(xml_id.split('.')[0] for xml_id in v)))
    return result


class ir_model(osv.osv):
    _name = 'ir.model'
    _description = "Objects"
    _order = 'model'

    def _is_osv_memory(self, cr, uid, ids, field_name, arg, context=None):
        models = self.browse(cr, uid, ids, context=context)
        res = dict.fromkeys(ids)
        for model in models:
            res[model.id] = isinstance(self.pool.get(model.model), osv.osv_memory)
        return res

    def _search_osv_memory(self, cr, uid, model, name, domain, context=None):
        if not domain:
            return []
        field, operator, value = domain[0]
        if operator not in ['=', '!=']:
            raise osv.except_osv(_('Invalid search criterions'), _('The osv_memory field can only be compared with = and != operator.'))
        value = bool(value) if operator == '=' else not bool(value)
        all_model_ids = self.search(cr, uid, [], context=context)
        is_osv_mem = self._is_osv_memory(cr, uid, all_model_ids, 'osv_memory', arg=None, context=context)
        return [('id', 'in', [id for id in is_osv_mem if bool(is_osv_mem[id]) == value])]

    def _view_ids(self, cr, uid, ids, field_name, arg, context=None):
        models = self.browse(cr, uid, ids)
        res = {}
        for model in models:
            res[model.id] = self.pool.get("ir.ui.view").search(cr, uid, [('model', '=', model.model)])
        return res

    _columns = {
        'name': fields.char('Object Name', size=64, translate=True, required=True),
        'model': fields.char('Object', size=64, required=True, select=1),
        'info': fields.text('Information'),
        'field_id': fields.one2many('ir.model.fields', 'model_id', 'Fields', required=True),
        'state': fields.selection([('manual','Custom Object'),('base','Base Object')],'Type',readonly=True),
        'access_ids': fields.one2many('ir.model.access', 'model_id', 'Access'),
        'osv_memory': fields.function(_is_osv_memory, method=True, string='In-memory model', type='boolean',
            fnct_search=_search_osv_memory,
            help="Indicates whether this object model lives in memory only, i.e. is not persisted (osv.osv_memory)"),
        'modules': fields.function(_in_modules, method=True, type='char', size=128, string='In modules', help='List of modules in which the object is defined or inherited'),
        'view_ids': fields.function(_view_ids, method=True, type='one2many', obj='ir.ui.view', string='Views'),
    }
    
    _defaults = {
        'model': lambda *a: 'x_',
        'state': lambda self,cr,uid,ctx=None: (ctx and ctx.get('manual',False)) and 'manual' or 'base',
    }
    
    def _check_model_name(self, cr, uid, ids, context=None):
        for model in self.browse(cr, uid, ids, context=context):
            if model.state=='manual':
                if not model.model.startswith('x_'):
                    return False
            if not re.match('^[a-z_A-Z0-9.]+$',model.model):
                return False
        return True

    def _model_name_msg(self, cr, uid, ids, context=None):
        return _('The Object name must start with x_ and not contain any special character !')
    _constraints = [
        (_check_model_name, _model_name_msg, ['model']),
    ]

    # overridden to allow searching both on model name (model field)
    # and model description (name field)
    def name_search(self, cr, uid, name='', args=None, operator='ilike',  context=None, limit=None):
        if args is None:
            args = []
        domain = args + ['|', ('model', operator, name), ('name', operator, name)]
        return super(ir_model, self).name_search(cr, uid, None, domain,
                        operator=operator, limit=limit, context=context)


    def unlink(self, cr, user, ids, context=None):
        for model in self.browse(cr, user, ids, context):
            if model.state != 'manual':
                raise except_orm(_('Error'), _("You can not remove the model '%s' !") %(model.name,))
        res = super(ir_model, self).unlink(cr, user, ids, context)
        pooler.restart_pool(cr.dbname)
        return res

    def write(self, cr, user, ids, vals, context=None):
        if context:
            context.pop('__last_update', None)
        return super(ir_model,self).write(cr, user, ids, vals, context)

    def create(self, cr, user, vals, context=None):
        if  context is None:
            context = {}
        if context and context.get('manual',False):
            vals['state']='manual'
        res = super(ir_model,self).create(cr, user, vals, context)
        if vals.get('state','base')=='manual':
            self.instanciate(cr, user, vals['model'], context)
            self.pool.get(vals['model']).__init__(self.pool, cr)
            ctx = context.copy()
            ctx.update({'field_name':vals['name'],'field_state':'manual','select':vals.get('select_level','0')})
            self.pool.get(vals['model'])._auto_init(cr, ctx)
            #pooler.restart_pool(cr.dbname)
        return res

    def instanciate(self, cr, user, model, context={}):
        class x_custom_model(osv.osv):
            pass
        x_custom_model._name = model
        x_custom_model._module = False
        a = x_custom_model.createInstance(self.pool, '', cr)
        if (not a._columns) or ('x_name' in a._columns.keys()):
            x_name = 'x_name'
        else:
            x_name = a._columns.keys()[0]
        x_custom_model._rec_name = x_name
ir_model()

class ir_model_fields(osv.osv):
    _name = 'ir.model.fields'
    _description = "Fields"

    _columns = {
        'name': fields.char('Name', required=True, size=64, select=1),
        'model': fields.char('Object Name', size=64, required=True, select=1,
            help="The technical name of the model this field belongs to"),
        'relation': fields.char('Object Relation', size=64,
            help="For relationship fields, the technical name of the target model"),
        'relation_field': fields.char('Relation Field', size=64,
            help="For one2many fields, the field on the target model that implement the opposite many2one relationship"),
        'model_id': fields.many2one('ir.model', 'Model', required=True, select=True, ondelete='cascade',
            help="The model this field belongs to"),
        'field_description': fields.char('Field Label', required=True, size=256),
        'ttype': fields.selection(_get_fields_type, 'Field Type',size=64, required=True),
        'selection': fields.char('Selection Options',size=128, help="List of options for a selection field, "
            "specified as a Python expression defining a list of (key, label) pairs. "
            "For example: [('blue','Blue'),('yellow','Yellow')]"),
        'required': fields.boolean('Required'),
        'readonly': fields.boolean('Readonly'),
        'select_level': fields.selection([('0','Not Searchable'),('1','Always Searchable'),('2','Advanced Search (deprecated)')],'Searchable', required=True),
        'translate': fields.boolean('Translate', help="Whether values for this field can be translated (enables the translation mechanism for that field)"),
        'size': fields.integer('Size'),
        'state': fields.selection([('manual','Custom Field'),('base','Base Field')],'Type', required=True, readonly=True, select=1),
        'on_delete': fields.selection([('cascade','Cascade'),('set null','Set NULL')], 'On delete', help='On delete property for many2one fields'),
        'domain': fields.char('Domain', size=256, help="The optional domain to restrict possible values for relationship fields, "
            "specified as a Python expression defining a list of triplets. "
            "For example: [('color','=','red')]"),
        'groups': fields.many2many('res.groups', 'ir_model_fields_group_rel', 'field_id', 'group_id', 'Groups'),
        'view_load': fields.boolean('View Auto-Load'),
        'selectable': fields.boolean('Selectable'),
        'modules': fields.function(_in_modules, method=True, type='char', size=128, string='In modules', help='List of modules in which the field is defined'),
    }
    _rec_name='field_description'
    _defaults = {
        'view_load': 0,
        'selection': "",
        'domain': "[]",
        'name': 'x_',
        'state': lambda self,cr,uid,ctx={}: (ctx and ctx.get('manual',False)) and 'manual' or 'base',
        'on_delete': 'set null',
        'select_level': '0',
        'size': 64,
        'field_description': '',
        'selectable': 1,
    }
    _order = "name"

    def _check_selection(self, cr, uid, selection, context=None):
        try:
            selection_list = eval(selection)
        except Exception:
            logging.getLogger('ir.model').warning('Invalid selection list definition for fields.selection', exc_info=True)
            raise except_orm(_('Error'),
                    _("The Selection Options expression is not a valid Pythonic expression." \
                      "Please provide an expression in the [('key','Label'), ...] format."))

        check = True
        if not (isinstance(selection_list, list) and selection_list):
            check = False
        else:
            for item in selection_list:
                if not (isinstance(item, (tuple,list)) and len(item) == 2):
                    check = False
                    break

        if not check:
                raise except_orm(_('Error'),
                    _("The Selection Options expression is must be in the [('key','Label'), ...] format!"))
        return True

    def _size_gt_zero_msg(self, cr, user, ids, context=None):
        return _('Size of the field can never be less than 1 !')

    _sql_constraints = [
        ('size_gt_zero', 'CHECK (size>0)',_size_gt_zero_msg ),
    ]

    def unlink(self, cr, user, ids, context=None):
        for field in self.browse(cr, user, ids, context):
            if field.state <> 'manual':
                raise except_orm(_('Error'), _("You cannot remove the field '%s' !") %(field.name,))
        #
        # MAY BE ADD A ALTER TABLE DROP ?
        #
            #Removing _columns entry for that table
            self.pool.get(field.model)._columns.pop(field.name,None)
        return super(ir_model_fields, self).unlink(cr, user, ids, context)

    def create(self, cr, user, vals, context=None):
        if 'model_id' in vals:
            model_data = self.pool.get('ir.model').browse(cr, user, vals['model_id'])
            vals['model'] = model_data.model
        if context is None:
            context = {}
        if context and context.get('manual',False):
            vals['state'] = 'manual'
        if vals.get('ttype', False) == 'selection':
            if not vals.get('selection',False):
                raise except_orm(_('Error'), _('For selection fields, the Selection Options must be given!'))
            self._check_selection(cr, user, vals['selection'], context=context)
        res = super(ir_model_fields,self).create(cr, user, vals, context)
        if vals.get('state','base') == 'manual':
            if not vals['name'].startswith('x_'):
                raise except_orm(_('Error'), _("Custom fields must have a name that starts with 'x_' !"))

            if vals.get('relation',False) and not self.pool.get('ir.model').search(cr, user, [('model','=',vals['relation'])]):
                 raise except_orm(_('Error'), _("Model %s does not exist!") % vals['relation'])

            if self.pool.get(vals['model']):
                self.pool.get(vals['model']).__init__(self.pool, cr)
                #Added context to _auto_init for special treatment to custom field for select_level
                ctx = context.copy()
                ctx.update({'field_name':vals['name'],'field_state':'manual','select':vals.get('select_level','0'),'update_custom_fields':True})
                self.pool.get(vals['model'])._auto_init(cr, ctx)

        return res

    def write(self, cr, user, ids, vals, context=None):
        if context is None:
            context = {}
        if context and context.get('manual',False):
            vals['state'] = 'manual'

        column_rename = None # if set, *one* column can be renamed here
        obj = None
        models_patch = {}    # structs of (obj, [(field, prop, change_to),..])
                             # data to be updated on the orm model

        # static table of properties
        model_props = [ # (our-name, fields.prop, set_fn)
            ('field_description', 'string', str),
            ('required', 'required', bool),
            ('readonly', 'readonly', bool),
            ('domain', '_domain', eval),
            ('size', 'size', int),
            ('on_delete', 'ondelete', str),
            ('translate', 'translate', bool),
            ('view_load', 'view_load', bool),
            ('selectable', 'selectable', bool),
            ('select_level', 'select', int),
            ('selection', 'selection', eval),
            ]

        if vals and ids:
            checked_selection = False # need only check it once, so defer

            for item in self.browse(cr, user, ids, context=context):
                if not (obj and obj._name == item.model):
                    obj = self.pool.get(item.model)

                if item.state != 'manual':
                    raise except_orm(_('Error!'),
                        _('Properties of base fields cannot be altered in this manner! '
                          'Please modify them through Python code, '
                          'preferably through a custom addon!'))

                if item.ttype == 'selection' and 'selection' in vals \
                        and not checked_selection:
                    self._check_selection(cr, user, vals['selection'], context=context)
                    checked_selection = True

                final_name = item.name
                if 'name' in vals and vals['name'] != item.name:
                    # We need to rename the column
                    if column_rename:
                        raise except_orm(_('Error!'), _('Can only rename one column at a time!'))
                    if vals['name'] in obj._columns:
                        raise except_orm(_('Error!'), _('Cannot rename column to %s, because that column already exists!') % vals['name'])
                    if vals.get('state', 'base') == 'manual' and not vals['name'].startswith('x_'):
                        raise except_orm(_('Error!'), _('New column name must still start with x_ , because it is a custom field!'))
                    if '\'' in vals['name'] or '"' in vals['name'] or ';' in vals['name']:
                        raise ValueError('Invalid character in column name')
                    column_rename = (obj, (obj._table, item.name, vals['name']))
                    final_name = vals['name']

                if 'model_id' in vals and vals['model_id'] != item.model_id:
                    raise except_orm(_("Error!"), _("Changing the model of a field is forbidden!"))

                if 'ttype' in vals and vals['ttype'] != item.ttype:
                    raise except_orm(_("Error!"), _("Changing the type of a column is not yet supported. "
                                "Please drop it and create it again!"))

                # We don't check the 'state', because it might come from the context
                # (thus be set for multiple fields) and will be ignored anyway.
                if obj:
                    models_patch.setdefault(obj._name, (obj,[]))
                    # find out which properties (per model) we need to update
                    for field_name, field_property, set_fn in model_props:
                        if field_name in vals:
                            property_value = set_fn(vals[field_name])
                            if getattr(obj._columns[item.name], field_property) != property_value:
                                models_patch[obj._name][1].append((final_name, field_property, property_value))
                        # our dict is ready here, but no properties are changed so far

        # These shall never be written (modified)
        for column_name in ('model_id', 'model', 'state'):
            if column_name in vals:
                del vals[column_name]

        res = super(ir_model_fields,self).write(cr, user, ids, vals, context=context)

        if column_rename:
            cr.execute('ALTER TABLE "%s" RENAME COLUMN "%s" TO "%s"' % column_rename[1])
            # This is VERY risky, but let us have this feature:
            # we want to change the key of column in obj._columns dict
            col = column_rename[0]._columns.pop(column_rename[1][1]) # take object out, w/o copy
            column_rename[0]._columns[column_rename[1][2]] = col

        if models_patch:
            # We have to update _columns of the model(s) and then call their
            # _auto_init to sync the db with the model. Hopefully, since write()
            # was called earlier, they will be in-sync before the _auto_init.
            # Anything we don't update in _columns now will be reset from
            # the model into ir.model.fields (db).
            ctx = context.copy()
            ctx.update({'select': vals.get('select_level','0'),'update_custom_fields':True})

            for model_key, patch_struct in models_patch.items():
                obj = patch_struct[0]
                for col_name, col_prop, val in patch_struct[1]:
                    setattr(obj._columns[col_name], col_prop, val)
                obj._auto_init(cr, ctx)
        return res

ir_model_fields()

class ir_model_access(osv.osv):
    _name = 'ir.model.access'
    _columns = {
        'name': fields.char('Name', size=64, required=True, select=True),
        'model_id': fields.many2one('ir.model', 'Object', required=True, domain=[('osv_memory','=', False)], select=True, ondelete='cascade'),
        'group_id': fields.many2one('res.groups', 'Group', ondelete='cascade', select=True),
        'perm_read': fields.boolean('Read Access'),
        'perm_write': fields.boolean('Write Access'),
        'perm_create': fields.boolean('Create Access'),
        'perm_unlink': fields.boolean('Delete Access'),
    }

    def check_groups(self, cr, uid, group):
        grouparr  = group.split('.')
        if not grouparr:
            return False
        cr.execute("select 1 from res_groups_users_rel where uid=%s and gid IN (select res_id from ir_model_data where module=%s and name=%s)", (uid, grouparr[0], grouparr[1],))
        return bool(cr.fetchone())

    def check_group(self, cr, uid, model, mode, group_ids):
        """ Check if a specific group has the access mode to the specified model"""
        assert mode in ['read','write','create','unlink'], 'Invalid access mode'

        if isinstance(model, browse_record):
            assert model._table_name == 'ir.model', 'Invalid model object'
            model_name = model.name
        else:
            model_name = model

        if isinstance(group_ids, (int, long)):
            group_ids = [group_ids]
        for group_id in group_ids:
            cr.execute("SELECT perm_" + mode + " "
                   "  FROM ir_model_access a "
                   "  JOIN ir_model m ON (m.id = a.model_id) "
                   " WHERE m.model = %s AND a.group_id = %s", (model_name, group_id)
                   )
            r = cr.fetchone()
            if r is None:
                cr.execute("SELECT perm_" + mode + " "
                       "  FROM ir_model_access a "
                       "  JOIN ir_model m ON (m.id = a.model_id) "
                       " WHERE m.model = %s AND a.group_id IS NULL", (model_name, )
                       )
                r = cr.fetchone()

            access = bool(r and r[0])
            if access:
                return True
        # pass no groups -> no access
        return False

    def check(self, cr, uid, model, mode='read', raise_exception=True, context=None):
        if uid==1:
            # User root have all accesses
            # TODO: exclude xml-rpc requests
            return True

        assert mode in ['read','write','create','unlink'], 'Invalid access mode'

        if isinstance(model, browse_record):
            assert model._table_name == 'ir.model', 'Invalid model object'
            model_name = model.name
        else:
            model_name = model

        # osv_memory objects can be read by everyone, as they only return
        # results that belong to the current user (except for superuser)
        model_obj = self.pool.get(model_name)
        if isinstance(model_obj, osv.osv_memory):
            return True

        # We check if a specific rule exists
        cr.execute('SELECT MAX(CASE WHEN perm_' + mode + ' THEN 1 ELSE 0 END) '
                   '  FROM ir_model_access a '
                   '  JOIN ir_model m ON (m.id = a.model_id) '
                   '  JOIN res_groups_users_rel gu ON (gu.gid = a.group_id) '
                   ' WHERE m.model = %s '
                   '   AND gu.uid = %s '
                   , (model_name, uid,)
                   )
        r = cr.fetchone()[0]

        if r is None:
            # there is no specific rule. We check the generic rule
            cr.execute('SELECT MAX(CASE WHEN perm_' + mode + ' THEN 1 ELSE 0 END) '
                       '  FROM ir_model_access a '
                       '  JOIN ir_model m ON (m.id = a.model_id) '
                       ' WHERE a.group_id IS NULL '
                       '   AND m.model = %s '
                       , (model_name,)
                       )
            r = cr.fetchone()[0]

        if not r and raise_exception:
            cr.execute('''select
                    g.name
                from
                    ir_model_access a 
                    left join ir_model m on (a.model_id=m.id) 
                    left join res_groups g on (a.group_id=g.id)
                where
                    m.model=%s and
                    a.group_id is not null and perm_''' + mode, (model_name, ))
            groups = ', '.join(map(lambda x: x[0], cr.fetchall())) or '/'
            msgs = {
                'read':   _("You can not read this document (%s) ! Be sure your user belongs to one of these groups: %s."),
                'write':  _("You can not write in this document (%s) ! Be sure your user belongs to one of these groups: %s."),
                'create': _("You can not create this document (%s) ! Be sure your user belongs to one of these groups: %s."),
                'unlink': _("You can not delete this document (%s) ! Be sure your user belongs to one of these groups: %s."),
            }

            raise except_orm(_('AccessError'), msgs[mode] % (model_name, groups) )
        return r

    check = tools.cache()(check)

    __cache_clearing_methods = []

    def register_cache_clearing_method(self, model, method):
        self.__cache_clearing_methods.append((model, method))

    def unregister_cache_clearing_method(self, model, method):
        try:
            i = self.__cache_clearing_methods.index((model, method))
            del self.__cache_clearing_methods[i]
        except ValueError:
            pass

    def call_cache_clearing_methods(self, cr):
        self.check.clear_cache(cr.dbname)    # clear the cache of check function
        for model, method in self.__cache_clearing_methods:
            object_ = self.pool.get(model)
            if object_:
                getattr(object_, method)()

    #
    # Check rights on actions
    #
    def write(self, cr, uid, *args, **argv):
        self.call_cache_clearing_methods(cr)
        res = super(ir_model_access, self).write(cr, uid, *args, **argv)
        return res

    def create(self, cr, uid, *args, **argv):
        self.call_cache_clearing_methods(cr)
        res = super(ir_model_access, self).create(cr, uid, *args, **argv)
        return res

    def unlink(self, cr, uid, *args, **argv):
        self.call_cache_clearing_methods(cr)
        res = super(ir_model_access, self).unlink(cr, uid, *args, **argv)
        return res

ir_model_access()

class ir_model_data(osv.osv):
    _name = 'ir.model.data'
    __logger = logging.getLogger('addons.base.'+_name)
    _order = 'module,model,name'
    _columns = {
        'name': fields.char('XML Identifier', required=True, size=128, select=1),
        'model': fields.char('Object', required=True, size=64, select=1),
        'module': fields.char('Module', required=True, size=64, select=1),
        'res_id': fields.integer('Resource ID', select=1),
        'noupdate': fields.boolean('Non Updatable'),
        'date_update': fields.datetime('Update Date'),
        'date_init': fields.datetime('Init Date')
    }
    _defaults = {
        'date_init': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'date_update': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'noupdate': False,
        'module': ''
    }
    _sql_constraints = [
        ('module_name_uniq', 'unique(name, module)', 'You cannot have multiple records with the same id for the same module !'),
    ]

    def __init__(self, pool, cr):
        osv.osv.__init__(self, pool, cr)
        self.doinit = True
        self.unlink_mark = {}

        # also stored in pool to avoid being discarded along with this osv instance
        if getattr(pool, 'model_data_reference_ids', None) is None:
            self.pool.model_data_reference_ids = {}
        self.loads = self.pool.model_data_reference_ids

    def _auto_init(self, cr, context=None):
        super(ir_model_data, self)._auto_init(cr, context)
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = \'ir_model_data_module_name_index\'')
        if not cr.fetchone():
            cr.execute('CREATE INDEX ir_model_data_module_name_index ON ir_model_data (module, name)')

    @tools.cache()
    def _get_id(self, cr, uid, module, xml_id):
        """Returns the id of the ir.model.data record corresponding to a given module and xml_id (cached) or raise a ValueError if not found"""
        ids = self.search(cr, uid, [('module','=',module), ('name','=', xml_id)])
        if not ids:
            raise ValueError('No references to %s.%s' % (module, xml_id))
        # the sql constraints ensure us we have only one result
        return ids[0]

    @tools.cache()
    def get_object_reference(self, cr, uid, module, xml_id):
        """Returns (model, res_id) corresponding to a given module and xml_id (cached) or raise ValueError if not found"""
        data_id = self._get_id(cr, uid, module, xml_id)
        res = self.read(cr, uid, data_id, ['model', 'res_id'])
        return (res['model'], res['res_id'])

    def get_object(self, cr, uid, module, xml_id, context=None):
        """Returns a browsable record for the given module name and xml_id or raise ValueError if not found"""
        res_model, res_id = self.get_object_reference(cr, uid, module, xml_id)
        return self.pool.get(res_model).browse(cr, uid, res_id, context=context)

    def _update_dummy(self,cr, uid, model, module, xml_id=False, store=True):
        if not xml_id:
            return False
        try:
            id = self.read(cr, uid, [self._get_id(cr, uid, module, xml_id)], ['res_id'])[0]['res_id']
            self.loads[(module,xml_id)] = (model,id)
        except:
            id = False
        return id

    def _update(self,cr, uid, model, module, values, xml_id=False, store=True, noupdate=False, mode='init', res_id=False, context=None):
        model_obj = self.pool.get(model)
        if not context:
            context = {}

        # records created during module install should result in res.log entries that are already read!
        context = dict(context, res_log_read=True)

        if xml_id and ('.' in xml_id):
            assert len(xml_id.split('.'))==2, _("'%s' contains too many dots. XML ids should not contain dots ! These are used to refer to other modules data, as in module.reference_id") % (xml_id)
            module, xml_id = xml_id.split('.')
        if (not xml_id) and (not self.doinit):
            return False
        action_id = False

        if xml_id:
            cr.execute('''SELECT imd.id, imd.res_id, md.id
                          FROM ir_model_data imd LEFT JOIN %s md ON (imd.res_id = md.id)
                          WHERE imd.module=%%s AND imd.name=%%s''' % model_obj._table,
                          (module, xml_id))
            results = cr.fetchall()
            for imd_id2,res_id2,real_id2 in results:
                if not real_id2:
                    self._get_id.clear_cache(cr.dbname, uid, module, xml_id)
                    self.get_object_reference.clear_cache(cr.dbname, uid, module, xml_id)
                    cr.execute('delete from ir_model_data where id=%s', (imd_id2,))
                    res_id = False
                else:
                    res_id,action_id = res_id2,imd_id2

        if action_id and res_id:
            model_obj.write(cr, uid, [res_id], values, context=context)
            self.write(cr, uid, [action_id], {
                'date_update': time.strftime('%Y-%m-%d %H:%M:%S'),
                },context=context)
        elif res_id:
            model_obj.write(cr, uid, [res_id], values, context=context)
            if xml_id:
                self.create(cr, uid, {
                    'name': xml_id,
                    'model': model,
                    'module':module,
                    'res_id':res_id,
                    'noupdate': noupdate,
                    },context=context)
                if model_obj._inherits:
                    for table in model_obj._inherits:
                        inherit_id = model_obj.browse(cr, uid,
                                res_id,context=context)[model_obj._inherits[table]]
                        self.create(cr, uid, {
                            'name': xml_id + '_' + table.replace('.', '_'),
                            'model': table,
                            'module': module,
                            'res_id': inherit_id.id,
                            'noupdate': noupdate,
                            },context=context)
        else:
            if mode=='init' or (mode=='update' and xml_id):
                res_id = model_obj.create(cr, uid, values, context=context)
                if xml_id:
                    self.create(cr, uid, {
                        'name': xml_id,
                        'model': model,
                        'module': module,
                        'res_id': res_id,
                        'noupdate': noupdate
                        },context=context)
                    if model_obj._inherits:
                        for table in model_obj._inherits:
                            inherit_id = model_obj.browse(cr, uid,
                                    res_id,context=context)[model_obj._inherits[table]]
                            self.create(cr, uid, {
                                'name': xml_id + '_' + table.replace('.', '_'),
                                'model': table,
                                'module': module,
                                'res_id': inherit_id.id,
                                'noupdate': noupdate,
                                },context=context)
        if xml_id:
            if res_id:
                self.loads[(module, xml_id)] = (model, res_id)
                if model_obj._inherits:
                    for table in model_obj._inherits:
                        inherit_field = model_obj._inherits[table]
                        inherit_id = model_obj.read(cr, uid, res_id,
                                [inherit_field])[inherit_field]
                        self.loads[(module, xml_id + '_' + \
                                table.replace('.', '_'))] = (table, inherit_id)
        return res_id

    def _unlink(self, cr, uid, model, res_ids):
        for res_id in res_ids:
            self.unlink_mark[(model, res_id)] = False
            cr.execute('delete from ir_model_data where res_id=%s and model=%s', (res_id, model))
        return True

    def ir_set(self, cr, uid, key, key2, name, models, value, replace=True, isobject=False, meta=None, xml_id=False):
        if type(models[0])==type([]) or type(models[0])==type(()):
            model,res_id = models[0]
        else:
            res_id=None
            model = models[0]

        if res_id:
            where = ' and res_id=%s' % (res_id,)
        else:
            where = ' and (res_id is null)'

        if key2:
            where += ' and key2=\'%s\'' % (key2,)
        else:
            where += ' and (key2 is null)'

        cr.execute('select * from ir_values where model=%s and key=%s and name=%s'+where,(model, key, name))
        res = cr.fetchone()
        if not res:
            res = ir.ir_set(cr, uid, key, key2, name, models, value, replace, isobject, meta)
        elif xml_id:
            cr.execute('UPDATE ir_values set value=%s WHERE model=%s and key=%s and name=%s'+where,(value, model, key, name))
        return True

    def _process_end(self, cr, uid, modules):
        if not modules:
            return True
        modules = list(modules)
        module_in = ",".join(["%s"] * len(modules))
        cr.execute('select id,name,model,res_id,module from ir_model_data where module IN (' + module_in + ') and noupdate=%s', modules + [False])
        wkf_todo = []
        for (id, name, model, res_id,module) in cr.fetchall():
            if (module,name) not in self.loads:
                self.unlink_mark[(model,res_id)] = id
                if model=='workflow.activity':
                    cr.execute('select res_type,res_id from wkf_instance where id IN (select inst_id from wkf_workitem where act_id=%s)', (res_id,))
                    wkf_todo.extend(cr.fetchall())
                    cr.execute("update wkf_transition set condition='True', group_id=NULL, signal=NULL,act_to=act_from,act_from=%s where act_to=%s", (res_id,res_id))
                    cr.execute("delete from wkf_transition where act_to=%s", (res_id,))

        for model,id in wkf_todo:
            wf_service = netsvc.LocalService("workflow")
            wf_service.trg_write(uid, model, id, cr)

        cr.commit()
        if not config.get('import_partial'):
            for (model, res_id) in self.unlink_mark.keys():
                if self.pool.get(model):
                    self.__logger.info('Deleting %s@%s', res_id, model)
                    try:
                        self.pool.get(model).unlink(cr, uid, [res_id])
                        if id:
                            ids = self.search(cr, uid, [('res_id','=',res_id),
                                                        ('model','=',model)])
                            self.__logger.debug('=> Deleting %s: %s',
                                                self._name, ids)
                            if len(ids) > 1 and \
                               self.__logger.isEnabledFor(logging.WARNING):
                                self.__logger.warn(
                                    'Got %d %s for (%s, %d): %s',
                                    len(ids), self._name, model, res_id,
                                    map(itemgetter('module','name'),
                                        self.read(cr, uid, ids,
                                                  ['name', 'module'])))
                            self.unlink(cr, uid, ids)
                            cr.execute(
                                'DELETE FROM ir_values WHERE value=%s',
                                ('%s,%s'%(model, res_id),))
                        cr.commit()
                    except Exception:
                        cr.rollback()
                        self.__logger.warn(
                            'Could not delete id: %d of model %s\nThere '
                            'should be some relation that points to this '
                            'resource\nYou should manually fix this and '
                            'restart with --update=module', res_id, model)
        return True
ir_model_data()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
