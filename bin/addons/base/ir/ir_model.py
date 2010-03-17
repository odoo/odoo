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

from osv import fields,osv
import ir, re
import netsvc
from osv.orm import except_orm, browse_record

import time
import tools
from tools import config
from tools.translate import _
import pooler

def _get_fields_type(self, cr, uid, context=None):
    cr.execute('select distinct ttype,ttype from ir_model_fields')
    return cr.fetchall()

class ir_model(osv.osv):
    _name = 'ir.model'
    _description = "Objects"
    _rec_name = 'name'
    _columns = {
        'name': fields.char('Object Name', size=64, translate=True, required=True),
        'model': fields.char('Object', size=64, required=True, select=1),
        'info': fields.text('Information'),
        'field_id': fields.one2many('ir.model.fields', 'model_id', 'Fields', required=True),
        'state': fields.selection([('manual','Custom Object'),('base','Base Object')],'Manually Created',readonly=True),
        'access_ids': fields.one2many('ir.model.access', 'model_id', 'Access'),
    }
    _defaults = {
        'model': lambda *a: 'x_',
        'state': lambda self,cr,uid,ctx={}: (ctx and ctx.get('manual',False)) and 'manual' or 'base',
    }
    def _check_model_name(self, cr, uid, ids):
        for model in self.browse(cr, uid, ids):
            if model.state=='manual':
                if not model.model.startswith('x_'):
                    return False
            if not re.match('^[a-z_A-Z0-9.]+$',model.model):
                return False
        return True

    _constraints = [
        (_check_model_name, 'The Object name must start with x_ and not contain any special character !', ['model']),
    ]
    def unlink(self, cr, user, ids, context=None):
        for model in self.browse(cr, user, ids, context):
            if model.state <> 'manual':
                raise except_orm(_('Error'), _("You can not remove the model '%s' !") %(model.name,))
        res = super(ir_model, self).unlink(cr, user, ids, context)
        pooler.restart_pool(cr.dbname)
        return res

    def write(self, cr, user, ids, vals, context=None):
        if context:
            context.pop('__last_update', None)
        return super(ir_model,self).write(cr, user, ids, vals, context)
        
    def create(self, cr, user, vals, context=None):
        if not context:
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
        x_custom_model.createInstance(self.pool, '', cr)
        x_custom_model._rec_name = 'x_name'
ir_model()


class ir_model_grid(osv.osv):
    _name = 'ir.model.grid'
    _table = 'ir_model'
    _inherit = 'ir.model'
    _description = "Objects Security Grid"

    def create(self, cr, uid, vals, context=None):
        raise osv.except_osv('Error !', 'You cannot add an entry to this view !')

    def unlink(self, *args, **argv):
        raise osv.except_osv('Error !', 'You cannot delete an entry of this view !')

    def read(self, cr, uid, ids, fields=None, context=None, load='_classic_read'):
        result = super(osv.osv, self).read(cr, uid, ids, fields, context, load)
        allgr = self.pool.get('res.groups').search(cr, uid, [], context=context)
        acc_obj = self.pool.get('ir.model.access')

        if not isinstance(result,list):
            result=[result]

        for res in result:
            rules = acc_obj.search(cr, uid, [('model_id', '=', res['id'])])
            rules_br = acc_obj.browse(cr, uid, rules, context=context)
            for g in allgr:
                res['group_'+str(g)] = ''
            for rule in rules_br:
                perm_list = []
                if rule.perm_read:
                    perm_list.append('r')
                if rule.perm_write:
                    perm_list.append('w')
                if rule.perm_create:
                    perm_list.append('c')
                if rule.perm_unlink:
                    perm_list.append('u')
                perms = ",".join(perm_list)
                if rule.group_id:
                    res['group_%d'%rule.group_id.id] = perms
                else:
                    res['group_0'] = perms
        return result

    #
    # This function do not write fields from ir.model because
    # access rights may be different for managing models and
    # access rights
    #
    def write(self, cr, uid, ids, vals, context=None):
        vals_new = vals.copy()
        acc_obj = self.pool.get('ir.model.access')
        for grid in self.browse(cr, uid, ids, context=context):
            model_id = grid.id
            perms_rel = ['read','write','create','unlink']
            for val in vals:
                if not val[:6]=='group_':
                    continue
                group_id = int(val[6:]) or False
                rules = acc_obj.search(cr, uid, [('model_id', '=', model_id),('group_id', '=', group_id)])
                if not rules:
                    rules = [acc_obj.create(cr, uid, {
                        'name': grid.name,
                        'model_id':model_id,
                        'group_id':group_id
                    }) ]
                vals2 = dict(map(lambda x: ('perm_'+x, x[0] in (vals[val] or '')), perms_rel))
                acc_obj.write(cr, uid, rules, vals2, context=context)
        return True

    def fields_get(self, cr, uid, fields=None, context=None, read_access=True):
        result = super(ir_model_grid, self).fields_get(cr, uid, fields, context)
        groups = self.pool.get('res.groups').search(cr, uid, [])
        groups_br = self.pool.get('res.groups').browse(cr, uid, groups)
        result['group_0'] = {'string': 'All Users','type': 'char','size': 7}
        for group in groups_br:
            result['group_%d'%group.id] = {'string': '%s'%group.name,'type': 'char','size': 7}
        return result

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context={}, toolbar=False):
        result = super(ir_model_grid, self).fields_view_get(cr, uid, view_id, view_type, context=context, toolbar=toolbar)
        groups = self.pool.get('res.groups').search(cr, uid, [])
        groups_br = self.pool.get('res.groups').browse(cr, uid, groups)
        cols = ['model', 'name']
        xml = '''<?xml version="1.0"?>
<%s editable="bottom">
    <field name="name" select="1" readonly="1" required="1"/>
    <field name="model" select="1" readonly="1" required="1"/>
    <field name="group_0"/>
    ''' % (view_type,)
        for group in groups_br:
            xml += '''<field name="group_%d"/>''' % (group.id, )
        xml += '''</%s>''' % (view_type,)
        result['arch'] = xml
        result['fields'] = self.fields_get(cr, uid, cols, context)
        return result
ir_model_grid()

class ir_model_fields(osv.osv):
    _name = 'ir.model.fields'
    _description = "Fields"
    _columns = {
        'name': fields.char('Name', required=True, size=64, select=1),
        'model': fields.char('Object Name', size=64, required=True),
        'relation': fields.char('Object Relation', size=64),
        'relation_field': fields.char('Relation Field', size=64),
        'model_id': fields.many2one('ir.model', 'Object ID', required=True, select=True, ondelete='cascade'),
        'field_description': fields.char('Field Label', required=True, size=256),
        'ttype': fields.selection(_get_fields_type, 'Field Type',size=64, required=True),
        'selection': fields.char('Field Selection',size=128),
        'required': fields.boolean('Required'),
        'readonly': fields.boolean('Readonly'),
        'select_level': fields.selection([('0','Not Searchable'),('1','Always Searchable'),('2','Advanced Search')],'Searchable', required=True),
        'translate': fields.boolean('Translate'),
        'size': fields.integer('Size'),
        'state': fields.selection([('manual','Custom Field'),('base','Base Field')],'Manually Created', required=True, readonly=True),
        'on_delete': fields.selection([('cascade','Cascade'),('set null','Set NULL')], 'On delete', help='On delete property for many2one fields'),
        'domain': fields.char('Domain', size=256),
        'groups': fields.many2many('res.groups', 'ir_model_fields_group_rel', 'field_id', 'group_id', 'Groups'),
        'view_load': fields.boolean('View Auto-Load'),
    }
    _rec_name='field_description'
    _defaults = {
        'view_load': lambda *a: 0,
        'selection': lambda *a: "[]",
        'domain': lambda *a: "[]",
        'name': lambda *a: 'x_',
        'state': lambda self,cr,uid,ctx={}: (ctx and ctx.get('manual',False)) and 'manual' or 'base',
        'on_delete': lambda *a: 'set null',
        'select_level': lambda *a: '0',
        'size': lambda *a: 64,
        'field_description': lambda *a: '',
    }
    _order = "id"
    _sql_constraints = [
        ('size_gt_zero', 'CHECK (size>0)', 'Size of the field can never be less than 1 !'),
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
        if not context:
            context = {}
        if context and context.get('manual',False):
            vals['state'] = 'manual'
        res = super(ir_model_fields,self).create(cr, user, vals, context)
        if vals.get('state','base') == 'manual':
            if not vals['name'].startswith('x_'):
                raise except_orm(_('Error'), _("Custom fields must have a name that starts with 'x_' !"))

            if 'relation' in vals and not self.pool.get('ir.model').search(cr, user, [('model','=',vals['relation'])]):
                 raise except_orm(_('Error'), _("Model %s Does not Exist !" % vals['relation']))

            if self.pool.get(vals['model']):
                self.pool.get(vals['model']).__init__(self.pool, cr)
                #Added context to _auto_init for special treatment to custom field for select_level
                ctx = context.copy()
                ctx.update({'field_name':vals['name'],'field_state':'manual','select':vals.get('select_level','0'),'update_custom_fields':True})
                self.pool.get(vals['model'])._auto_init(cr, ctx)

        return res
    
ir_model_fields()

class ir_model_access(osv.osv):
    _name = 'ir.model.access'
    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'model_id': fields.many2one('ir.model', 'Object', required=True),
        'group_id': fields.many2one('res.groups', 'Group'),
        'perm_read': fields.boolean('Read Access'),
        'perm_write': fields.boolean('Write Access'),
        'perm_create': fields.boolean('Create Access'),
        'perm_unlink': fields.boolean('Delete Permission'),
    }

    def check_groups(self, cr, uid, group):
        res = False
        grouparr  = group.split('.')
        if not grouparr:
            return False

        cr.execute("select 1 from res_groups_users_rel where uid=%s and gid in(select res_id from ir_model_data where module=%s and name=%s)", (uid, grouparr[0], grouparr[1],))
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
            msgs = {
                'read':   _('You can not read this document! (%s)'),
                'write':  _('You can not write in this document! (%s)'),
                'create': _('You can not create this kind of document! (%s)'),
                'unlink': _('You can not delete this document! (%s)'),
            }
            raise except_orm(_('AccessError'), msgs[mode] % model_name )
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
            getattr(self.pool.get(model), method)()

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
    _columns = {
        'name': fields.char('XML Identifier', required=True, size=128),
        'model': fields.char('Object', required=True, size=64),
        'module': fields.char('Module', required=True, size=64),
        'res_id': fields.integer('Resource ID'),
        'noupdate': fields.boolean('Non Updatable'),
        'date_update': fields.datetime('Update Date'),
        'date_init': fields.datetime('Init Date')
    }
    _defaults = {
        'date_init': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'date_update': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'noupdate': lambda *a: False,
        'module': lambda *a: ''
    }
    _sql_constraints = [
        ('module_name_uniq', 'unique(name, module)', 'You cannot have multiple records with the same id for the same module'),
    ]

    def __init__(self, pool, cr):
        osv.osv.__init__(self, pool, cr)
        self.loads = {}
        self.doinit = True
        self.unlink_mark = {}

    @tools.cache()
    def _get_id(self, cr, uid, module, xml_id):
        ids = self.search(cr, uid, [('module','=',module),('name','=', xml_id)])
        if not ids:
            raise Exception('No references to %s.%s' % (module, xml_id))
        # the sql constraints ensure us we have only one result
        return ids[0]

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
        warning = True
        model_obj = self.pool.get(model)
        if not context:
            context = {}
        if xml_id and ('.' in xml_id):
            assert len(xml_id.split('.'))==2, _('"%s" contains too many dots. XML ids should not contain dots ! These are used to refer to other modules data, as in module.reference_id') % (xml_id)
            warning = False
            module, xml_id = xml_id.split('.')
        if (not xml_id) and (not self.doinit):
            return False
        action_id = False

        if xml_id:
            cr.execute('select id,res_id from ir_model_data where module=%s and name=%s', (module,xml_id))
            results = cr.fetchall()
            for action_id2,res_id2 in results:
                cr.execute('select id from '+model_obj._table+' where id=%s', (res_id2,))
                result3 = cr.fetchone()
                if not result3:
                    self._get_id.clear_cache(cr.dbname, uid, module, xml_id)
                    cr.execute('delete from ir_model_data where id=%s', (action_id2,))
                    res_id = False
                else:
                    res_id,action_id = res_id2,action_id2

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
                            'res_id': inherit_id,
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
                                'res_id': inherit_id,
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

    def _unlink(self, cr, uid, model, ids, direct=False):
        for id in ids:
            self.unlink_mark[(model, id)]=False
            cr.execute('delete from ir_model_data where res_id=%s and model=%s', (id, model))
        return True

    def ir_set(self, cr, uid, key, key2, name, models, value, replace=True, isobject=False, meta=None, xml_id=False):
        obj = self.pool.get('ir.values')
        if type(models[0])==type([]) or type(models[0])==type(()):
            model,res_id = models[0]
        else:
            res_id=None
            model = models[0]

        clause = "model=%s AND key=%s AND name=%s"
        params = (model, key, name)
        if res_id:
            clause += ' AND res_id=%s'
            params += (res_id,)
        else:
            clause += ' AND (res_id IS NULL)'

        if key2:
            clause += ' AND key2=%s'
            params += (key2,)
        else:
            clause += ' AND (key2 IS NULL)'

        cr.execute('SELECT 1 FROM ir_values WHERE ' + clause, params)
        res = cr.fetchone()
        if not res:
            ir.ir_set(cr, uid, key, key2, name, models, value, replace, isobject, meta)
        elif xml_id:
            cr.execute('UPDATE ir_values SET value=%s WHERE ' + clause, (value,) + params)
        return True

    def _process_end(self, cr, uid, modules):
        if not modules:
            return True
        cr.execute('select id,name,model,res_id,module from ir_model_data where module in %s and noupdate=%s', (tuple(modules), False))
        wkf_todo = []
        for (id, name, model, res_id,module) in cr.fetchall():
            if (module,name) not in self.loads:
                self.unlink_mark[(model,res_id)] = id
                if model=='workflow.activity':
                    cr.execute('select res_type,res_id from wkf_instance where id in (select inst_id from wkf_workitem where act_id=%s)', (res_id,))
                    wkf_todo.extend(cr.fetchall())
                    cr.execute("update wkf_transition set condition='True', role_id=NULL, signal=NULL,act_to=act_from,act_from=%s where act_to=%s", (res_id,res_id))
                    cr.execute("delete from wkf_transition where act_to=%s", (res_id,))

        for model,id in wkf_todo:
            wf_service = netsvc.LocalService("workflow")
            wf_service.trg_write(uid, model, id, cr)

        cr.commit()
        if not config.get('import_partial', False):
            logger = netsvc.Logger()
            for (model, res_id) in self.unlink_mark.keys():
                if self.pool.get(model):
                    logger.notifyChannel('init', netsvc.LOG_INFO, 'Deleting %s@%s' % (res_id, model))
                    try:
                        self.pool.get(model).unlink(cr, uid, [res_id])
                        id = self.unlink_mark[(model, res_id)]
                        if id:
                            self.unlink(cr, uid, [id])
                            cr.execute('DELETE FROM ir_values WHERE value=%s', ('%s,%s' % (model, res_id),))
                        cr.commit()
                    except Exception, e:
                        cr.rollback()
                        logger.notifyChannel('init', netsvc.LOG_ERROR, e)
                        logger.notifyChannel('init', netsvc.LOG_ERROR, 'Could not delete id: %d of model %s\nThere should be some relation that points to this resource\nYou should manually fix this and restart --update=module' % (res_id, model))
        return True
ir_model_data()

class ir_model_config(osv.osv):
    _name = 'ir.model.config'
    _columns = {
        'password': fields.char('Password', size=64),
        'password_check': fields.char('Confirmation', size=64),
    }

    def action_cancel(self, cr, uid, ids, context={}):
        return {
            'view_type': 'form',
            "view_mode": 'form',
            'res_model': 'ir.actions.configuration.wizard',
            'type': 'ir.actions.act_window',
            'target':'new',
        }

    def action_update_pw(self, cr, uid, ids, context={}):
        res = self.read(cr,uid,ids)[0]
        root = self.pool.get('res.users').browse(cr, uid, [1])[0]
        self.unlink(cr, uid, [res['id']])
        if res['password']!=res['password_check']:
            raise except_orm(_('Error'), _("Password mismatch !"))
        elif not res['password']:
            raise except_orm(_('Error'), _("Password empty !"))
        self.pool.get('res.users').write(cr, uid, [root.id], {'password':res['password']})
        return {
            'view_type': 'form',
            "view_mode": 'form',
            'res_model': 'ir.actions.configuration.wizard',
            'type': 'ir.actions.act_window',
            'target':'new',
        }
ir_model_config()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
