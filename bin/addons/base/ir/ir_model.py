# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2004-2008 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id$
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

from osv import fields,osv
import ir, re
import netsvc
from osv.orm import except_orm

import time
import tools
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
        'model': fields.char('Object Name', size=64, required=True, search=1),
        'info': fields.text('Information'),
        'field_id': fields.one2many('ir.model.fields', 'model_id', 'Fields', required=True),
        'state': fields.selection([('manual','Custom Object'),('base','Base Field')],'Manualy Created',readonly=1),
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
            if not re.match('^[a-z_A-Z0-9]+$',model.model):
                return False
        return True

    _constraints = [
        (_check_model_name, 'The Object name must start with x_ and not contain any special character !', ['model']),
    ]
    def unlink(self, cr, user, ids, context=None):
        for model in self.browse(cr, user, ids, context):
            if model.state <> 'manual':
                raise except_orm(_('Error'), _("You can not remove the model '%s' !") %(field.name,))
        res = super(ir_model, self).unlink(cr, user, ids, context)
        pooler.restart_pool(cr.dbname)
        return res

    def create(self, cr, user, vals, context=None):
        if context and context.get('manual',False):
            vals['state']='manual'
        res = super(ir_model,self).create(cr, user, vals, context)
        if vals.get('state','base')=='manual':
            pooler.restart_pool(cr.dbname)
        return res

    def instanciate(self, cr, user, model, context={}):
        class x_custom_model(osv.osv):
            pass
        x_custom_model._name = model
        x_custom_model._module = False
        x_custom_model.createInstance(self.pool, '', cr)
        if 'x_name' in x_custom_model._columns:
            x_custom_model._rec_name = 'x_name'
        else:
            x_custom_model._rec_name = x_custom_model._columns.keys()[0]
ir_model()

class ir_model_fields(osv.osv):
    _name = 'ir.model.fields'
    _description = "Fields"
    _columns = {
        'name': fields.char('Name', required=True, size=64, select=1),
        'model': fields.char('Object Name', size=64, required=True),
        'relation': fields.char('Object Relation', size=64),
        'model_id': fields.many2one('ir.model', 'Object id', required=True, select=True, ondelete='cascade'),
        'field_description': fields.char('Field Label', required=True, size=256),
        'relate': fields.boolean('Click and Relate'),

        'ttype': fields.selection(_get_fields_type, 'Field Type',size=64, required=True),
        'selection': fields.char('Field Selection',size=128),
        'required': fields.boolean('Required'),
        'readonly': fields.boolean('Readonly'),
        'select_level': fields.selection([('0','Not Searchable'),('1','Always Searchable'),('2','Advanced Search')],'Searchable', required=True),
        'translate': fields.boolean('Translate'),
        'size': fields.integer('Size'),
        'state': fields.selection([('manual','Custom Field'),('base','Base Field')],'Manualy Created'),
        'on_delete': fields.selection([('cascade','Cascade'),('set null','Set NULL')], 'On delete', help='On delete property for many2one fields'),
        'domain': fields.char('Domain', size=256),

        'groups': fields.many2many('res.groups', 'ir_model_fields_group_rel', 'field_id', 'group_id', 'Groups'),
        'view_load': fields.boolean('View Auto-Load'),
    }
    _defaults = {
        'relate': lambda *a: 0,
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
    def unlink(self, cr, user, ids, context=None):
        for field in self.browse(cr, user, ids, context):
            if field.state <> 'manual':
                raise except_orm(_('Error'), _("You can not remove the field '%s' !") %(field.name,))
        #
        # MAY BE ADD A ALTER TABLE DROP ?
        #
        return super(ir_model_fields, self).unlink(cr, user, ids, context)

    def create(self, cr, user, vals, context=None):
        if 'model_id' in vals:
            model_data=self.pool.get('ir.model').browse(cr,user,vals['model_id'])
            vals['model']=model_data.model
        if context and context.get('manual',False):
            vals['state']='manual'
        res = super(ir_model_fields,self).create(cr, user, vals, context)
        if vals.get('state','base')=='manual':
            if not vals['name'].startswith('x_'):
                raise except_orm(_('Error'), _("Custom fields must have a name that starts with 'x_' !"))
            if self.pool.get(vals['model']):
                self.pool.get(vals['model']).__init__(self.pool, cr)
                self.pool.get(vals['model'])._auto_init(cr,{})
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
        if grouparr:
            cr.execute("select * from res_groups_users_rel where uid=" + str(uid) + " and gid in(select res_id from ir_model_data where module='%s' and name='%s')" % (grouparr[0], grouparr[1]))
            r = cr.fetchall()   
            if not r:
                res = False
            else:
                res = True
        else:
            res = False
        return res
    
    def check(self, cr, uid, model_name, mode='read',raise_exception=True):
        assert mode in ['read','write','create','unlink'], 'Invalid access mode for security'
        if uid == 1:
            return True

        cr.execute('SELECT MAX(CASE WHEN perm_'+mode+' THEN 1 else 0 END) '
            'FROM ir_model_access a '
                'JOIN ir_model m '
                    'ON (a.model_id=m.id) '
                'JOIN res_groups_users_rel gu '
                    'ON (gu.gid = a.group_id) '
            'WHERE m.model = %s AND gu.uid = %s', (model_name, uid,))
        r = cr.fetchall()
        if r[0][0] == None:
            cr.execute('SELECT MAX(CASE WHEN perm_'+mode+' THEN 1 else 0 END) '
                'FROM ir_model_access a '
                    'JOIN ir_model m '
                        'ON (a.model_id = m.id) '
                'WHERE a.group_id IS NULL AND m.model = %s', (model_name,))
            r= cr.fetchall()
            if r[0][0] == None:
                return True # Changed waiting final rules
                #return False # by default, the user had no access

        if not r[0][0]:
            if raise_exception:
                msgs = {
                        'read':   _('You can not read this document! (%s)'),
                        'write':  _('You can not write in this document! (%s)'),
                        'create': _('You can not create this kind of document! (%s)'),
                        'unlink': _('You can not delete this document! (%s)'),
                        }
                # due to the assert at the begin of the function, we will never have a KeyError
                raise except_orm(_('AccessError'), msgs[mode] % model_name )
        return r[0][0]

    check = tools.cache()(check)

    #
    # Methods to clean the cache on the Check Method.
    #
    def write(self, cr, uid, *args, **argv):
        res = super(ir_model_access, self).write(cr, uid, *args, **argv)
        self.check()
        return res
    def create(self, cr, uid, *args, **argv):
        res = super(ir_model_access, self).create(cr, uid, *args, **argv)
        self.check()
        return res
    def unlink(self, cr, uid, *args, **argv):
        res = super(ir_model_access, self).unlink(cr, uid, *args, **argv)
        self.check()
        return res
ir_model_access()

class ir_model_data(osv.osv):
    _name = 'ir.model.data'
    _columns = {
        'name': fields.char('XML Identifier', required=True, size=64),
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
        'noupdate': lambda *a: False
    }

    def __init__(self, pool, cr):
        osv.osv.__init__(self, pool, cr)
        self.loads = {}
        self.doinit = True
        self.unlink_mark = {}

    def _get_id(self,cr, uid, module, xml_id):
        ids = self.search(cr, uid, [('module','=',module),('name','=', xml_id)])
        assert len(ids)==1, '%d reference(s) to %s. You should have only one !' % (len(ids),xml_id)
        return ids[0]
    _get_id = tools.cache()(_get_id)

    def _update_dummy(self,cr, uid, model, module, xml_id=False, store=True):
        if not xml_id:
            return False
        try:
            id = self.read(cr, uid, [self._get_id(cr, uid, module, xml_id)], ['res_id'])[0]['res_id']
            self.loads[(module,xml_id)] = (model,id)
        except:
            id = False
        return id

    def _update(self,cr, uid, model, module, values, xml_id=False, store=True, noupdate=False, mode='init', res_id=False):
        warning = True
        model_obj = self.pool.get(model)
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
                cr.execute('select id from '+self.pool.get(model)._table+' where id=%d', (res_id2,))
                result3 = cr.fetchone()
                if not result3:
                    cr.execute('delete from ir_model_data where id=%d', (action_id2,))
                else:
                    res_id,action_id = res_id2,action_id2

        if action_id and res_id:
            model_obj.write(cr, uid, [res_id], values)
            self.write(cr, uid, [action_id], {
                'date_update': time.strftime('%Y-%m-%d %H:%M:%S'),
                })
        elif res_id:
            model_obj.write(cr, uid, [res_id], values)
            if xml_id:
                self.create(cr, uid, {
                    'name': xml_id,
                    'model': model,
                    'module':module,
                    'res_id':res_id,
                    'noupdate': noupdate,
                    })
                if model_obj._inherits:
                    for table in model_obj._inherits:
                        inherit_id = model_obj.browse(cr, uid,
                                res_id)[model_obj._inherits[table]]
                        self.create(cr, uid, {
                            'name': xml_id + '_' + table.replace('.', '_'),
                            'model': table,
                            'module': module,
                            'res_id': inherit_id,
                            'noupdate': noupdate,
                            })
        else:
            if mode=='init' or (mode=='update' and xml_id):
                res_id = model_obj.create(cr, uid, values)
                if xml_id:
                    self.create(cr, uid, {
                        'name': xml_id,
                        'model': model,
                        'module': module,
                        'res_id': res_id,
                        'noupdate': noupdate
                        })
                    if model_obj._inherits:
                        for table in model_obj._inherits:
                            inherit_id = model_obj.browse(cr, uid,
                                    res_id)[model_obj._inherits[table]]
                            self.create(cr, uid, {
                                'name': xml_id + '_' + table.replace('.', '_'),
                                'model': table,
                                'module': module,
                                'res_id': inherit_id,
                                'noupdate': noupdate,
                                })
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
        #self.pool.get(model).unlink(cr, uid, ids)
        for id in ids:
            self.unlink_mark[(model, id)]=False
            cr.execute('delete from ir_model_data where res_id=%d and model=\'%s\'', (id,model))
        return True

    def ir_set(self, cr, uid, key, key2, name, models, value, replace=True, isobject=False, meta=None, xml_id=False):
        obj = self.pool.get('ir.values')
        if type(models[0])==type([]) or type(models[0])==type(()):
            model,res_id = models[0]
        else:
            res_id=None
            model = models[0]

        if res_id:
            where = ' and res_id=%d' % (res_id,)
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
        module_str = ["'%s'" % m for m in modules]
        cr.execute('select id,name,model,res_id,module from ir_model_data where module in ('+','.join(module_str)+') and not noupdate')
        wkf_todo = []
        for (id, name, model, res_id,module) in cr.fetchall():
            if (module,name) not in self.loads:
                self.unlink_mark[(model,res_id)] = id
                if model=='workflow.activity':
                    cr.execute('select res_type,res_id from wkf_instance where id in (select inst_id from wkf_workitem where act_id=%d)', (res_id,))
                    wkf_todo.extend(cr.fetchall())
                    cr.execute("update wkf_transition set condition='True', role_id=NULL, signal=NULL,act_to=act_from,act_from=%d where act_to=%d", (res_id,res_id))
                    cr.execute("delete from wkf_transition where act_to=%d", (res_id,))

        for model,id in wkf_todo:
            wf_service = netsvc.LocalService("workflow")
            wf_service.trg_write(uid, model, id, cr)

        cr.commit()
        for (model,id) in self.unlink_mark.keys():
            if self.pool.get(model):
                logger = netsvc.Logger()
                logger.notifyChannel('init', netsvc.LOG_INFO, 'Deleting %s@%s' % (id, model))
                try:
                    self.pool.get(model).unlink(cr, uid, [id])
                    if self.unlink_mark[(model,id)]:
                        self.unlink(cr, uid, [self.unlink_mark[(model,id)]])
                        cr.execute('DELETE FROM ir_values WHERE value=%s', (model+','+str(id),))
                    cr.commit()
                except:
                    logger.notifyChannel('init', netsvc.LOG_ERROR, 'Could not delete id: %d of model %s\tThere should be some relation that points to this resource\tYou should manually fix this and restart --update=module' % (id, model))
        return True
ir_model_data()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

