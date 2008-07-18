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

from pprint import pprint #FIXME: Dev

def _get_fields_type(self, cr, uid, context=None):
    cr.execute('select distinct ttype,ttype from ir_model_fields')
    return cr.fetchall()


class ir_model_type(osv.osv):
    _name = 'ir.model.type'
    _columns = {
        'name': fields.char('Name', size=64, required=True),
        #'model_id': fields.many2one('ir.model', 'Models'),
    }
ir_model_type()

class ir_model(osv.osv):
    _name = 'ir.model'
    _description = "Objects"
    _rec_name = 'name'
    _columns = {
        'name': fields.char('Model Name', size=64, translate=True, required=True),
        'model': fields.char('Object Name', size=64, required=True, search=1),
        'info': fields.text('Information'),
        'field_id': fields.one2many('ir.model.fields', 'model_id', 'Fields', required=True),
        #'type_id': fields.one2many('ir.model.type', 'model_id', 'Type'),
        #'type_id': fields.many2many('ir.model.type', 'ir_model_type_rel', 'model_id', 'type_id', 'Types'),
        'state': fields.selection([('manual','Custom Object'),('base','Base Field')],'Manualy Created',readonly=1),
    }
    _defaults = {
        'model': lambda *a: 'x_',
        'state': lambda self,cr,uid,ctx={}: (ctx and ctx.get('manual',False)) and 'manual' or 'base',
    }
    
    #FIXME: We'll be back soon 
    #_constraints = [
    #    (_check_model_name, 'The model name must start with x_ and not contain any special character !', ['model']),
    #]
    
    def _check_model_name(self, cr, uid, ids):
        for model in self.browse(cr, uid, ids):
            if model.state=='manual':
                if not model.model.startswith('x_'):
                    return False
            if not re.match('^[a-z_A-Z0-9]+$',model.model):
                return False
        return True

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
    
    def unlink(self, cr, user, ids, context=None):
        #TODO Advanced
        for model in self.browse(cr, user, ids, context):
            if model.state <> 'manual':
                raise except_orm(_('Error'), _("You can not remove the model '%s' !") %(field.name,))
        res = super(ir_model, self).unlink(cr, user, ids, context)
        pooler.restart_pool(cr.dbname)
        return res

    def create(self, cr, user, vals, context=None):
        #TODO Advanced
        if context and context.get('manual',False):
            vals['state']='manual'
        res = super(ir_model,self).create(cr, user, vals, context)
        if vals.get('state','base')=='manual':
            pooler.restart_pool(cr.dbname)
        return res
    
    def read(self, cr, user, ids, fields=None, context=None, load='_classic_read'):
        result = super(osv.osv, self).read(cr, user, ids, fields, context, load)
        if 'advanced' in context:
            for res in result:
                rules = self.pool.get('ir.model.access').search(cr, user, [('model_id', '=', res['id'])])
                rules_br = self.pool.get('ir.model.access').browse(cr, user, rules)
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
                    res['group_%i'%rule.group_id.id] = perms
        return result

    def write(self, cr, user, ids, vals, context=None):
        if 'advanced' in context:
            perms_rel = ['create','read','unlink','write']
            perms_all = ['c','r','u','w']
            perms = []
            vals_new = vals.copy()
            
            for val in vals:
                if val[:6]=='group_':
                    #Values
                    group_id = int(val[6:])
                    model_id = ids[0]
                    if isinstance(vals[val], basestring):
                        perms = list(set(vals[val].split(",")))
                    
                    #Syntax check
                    for perm in perms:
                        if perm not in perms_all:
                            model_name = self.pool.get('ir.model').browse(cr, user, [model_id])[0].model
                            group_name = self.pool.get('res.groups').browse(cr, user, [group_id])[0].name
                            raise osv.except_osv('Error !', 'There is an invalid rule in "%s" for "Group %s". Valid rules are:\r\tc=create\r\tr=read\r\tu=unlink\r\tw=write\rYou must separate them by a coma, example: r,w'%(model_name, group_name))
                    
                    #Assign rights
                    req = {}
                    for i,perm in enumerate(perms_all):
                        #if perm in perms:
                        #    req['perm_%s'%perms_rel[i]] = True
                        #else:
                        #    req['perm_%s'%perms_rel[i]] = False
                        req['perm_%s'%perms_rel[i]] = perm in perms and 'True' or 'False'
                    
                    #Apply rule
                    sql = ''
                    rules = self.pool.get('ir.model.access').search(cr, user, [('model_id', '=', model_id),('group_id', '=', group_id)])
                    if rules:
                        for k in req:
                            sql += '%s=%s,'%(k,req[k])
                        cr.execute("update ir_model_access set %s where id=%i"%(sql[:-1], rules[0]))
                    else:
                        model_name = self.pool.get('ir.model').browse(cr, user, [model_id])[0].name
                        group_name = self.pool.get('res.groups').browse(cr, user, [group_id])[0].name
                        rule_name = '%s %s'%(model_name,group_name)
                        cr.execute('insert into ir_model_access \
                            (name, model_id, group_id, perm_create, perm_read, perm_unlink, perm_write) \
                            values (%s, %i, %i, %s, %s, %s, %s)',
                            (rule_name, model_id, group_id,req['perm_create'], req['perm_read'], req['perm_unlink'], req['perm_write'],))
                    vals_new.pop(val)
        return super(osv.osv, self).write(cr, user, ids, vals_new, context)
    
    def fields_get(self, cr, user, fields=None, context=None, read_access=True):
        result = super(osv.osv, self).fields_get(cr, user, fields, context)
        if 'advanced' in context:
            groups = self.pool.get('res.groups').search(cr, user, [])
            groups_br = self.pool.get('res.groups').browse(cr, user, groups)
            for group in groups_br:
                result['group_%i'%group.id] = {'string': 'Group %s'%group.name,'type': 'char','size': 7}
        return result
    
    def on_change_write(self, cr, user, ids, vals, context=None):
        print 'prout'
    
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context={}, toolbar=False):
        result = super(osv.osv, self).fields_view_get(cr, uid, view_id,view_type,context)
        if view_type=='tree' and 'advanced' in context:
            groups = self.pool.get('res.groups').search(cr, uid, [])
            groups_br = self.pool.get('res.groups').browse(cr, uid, groups)
            
            #state = ''
            #TODO: qqch du genre si un object n'a pas de secu
            #for field in journal.view_id.columns_id:
            #    if field.field=='state':
            #        state = ' colors="red:state==\'draft\'"'
            
            cols = ['model']
            xml = '''<?xml version="1.0"?><tree editable="top"><field name="model" readonly="1"/>'''
            for group in groups_br:
                #xml += '''<field name="group_%i" sum="%s" on_change="on_change_write()"/>''' % (group.id, group.name) #TODO: on_change
                xml += '''<field name="group_%i" sum="%s"/>''' % (group.id, group.name)
            xml += '''</tree>'''
            
            result['arch'] = xml
            result['fields'] = self.fields_get(cr, uid, cols, context)
        return result
ir_model()

class ir_model_fields(osv.osv):
    _name = 'ir.model.fields'
    _description = "Fields"
    _columns = {
        'name': fields.char('Name', required=True, size=64, select=1),
        'model': fields.char('Object Name', size=64, required=True),
        'relation': fields.char('Model Relation', size=64),
        'model_id': fields.many2one('ir.model', 'Model id', required=True, select=True, ondelete='cascade'),
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
        'group_name': fields.char('Group Name', size=128),
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
        return super(ir_model_fields, self).unlink(cr, user, ids, context)

    def create(self, cr, user, vals, context=None):
        if 'model_id' in vals:
            model_data=self.pool.get('ir.model').read(cr,user,vals['model_id'])
            vals['model']=model_data['model']
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
        'model_id': fields.many2one('ir.model', 'Model', required=True),
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
            cr.execute("select * from res_groups_users_rel where uid=" + str(uid) + " and gid in(select res_id from ir_model_data where module='%s' and name='%s')", (grouparr[0], grouparr[1],))
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
        # Users root and admin have all access (Todo: exclude xml-rpc requests)
        if uid==1 or uid==2:
            return True
        
        # We check if a specific rule exists
        cr.execute('SELECT MAX(CASE WHEN perm_'+mode+' THEN 1 else 0 END) '
            'from ir_model_access a join ir_model m on (m.id=a.model_id) '
                'join res_groups_users_rel gu on (gu.gid = a.group_id) '
            'where m.model = %s and gu.uid = %s', (model_name, uid,))
        r = cr.fetchall()
        
        print '%s in %s = %s by %i'%(mode, model_name, str(r[0][0]), uid) # FIXME: REMOVE PLEASE
        
        if not r[0][0]:
            if raise_exception:
                msgs = {
                        'read':   _('You can not read this document! (%s)'),
                        'write':  _('You can not write in this document! (%s)'),
                        'create': _('You can not create this kind of document! (%s)'),
                        'unlink': _('You can not delete this document! (%s)'),
                        }
                raise except_orm(_('AccessError'), msgs[mode] % model_name )
        return r[0][0]

    check = tools.cache()(check)

    #
    # Check rights on actions
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
        'model': fields.char('Model', required=True, size=64),
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

