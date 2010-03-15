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

from osv import osv,fields
from osv.orm import except_orm
import pickle

class ir_values(osv.osv):
    _name = 'ir.values'

    def _value_unpickle(self, cursor, user, ids, name, arg, context=None):
        res = {}
        for report in self.browse(cursor, user, ids, context=context):
            value = report[name[:-9]]
            if not report.object and value:
                try:
                    value = str(pickle.loads(value))
                except:
                    pass
            res[report.id] = value
        return res

    def _value_pickle(self, cursor, user, id, name, value, arg, context=None):
        if context is None:
            context = {}
        ctx = context.copy()
        if self.CONCURRENCY_CHECK_FIELD in ctx:
            del ctx[self.CONCURRENCY_CHECK_FIELD]
        if not self.browse(cursor, user, id, context=context).object:
            value = pickle.dumps(value)
        self.write(cursor, user, id, {name[:-9]: value}, context=ctx)

    def onchange_object_id(self, cr, uid, ids, object_id, context={}):
        if not object_id: return {}
        act = self.pool.get('ir.model').browse(cr, uid, object_id, context=context)
        return {
                'value': {'model': act.model}
        }

    def onchange_action_id(self, cr, uid, ids, action_id, context={}):
        if not action_id: return {}
        act = self.pool.get('ir.actions.actions').browse(cr, uid, action_id, context=context)
        return {
                'value': {'value_unpickle': act.type+','+str(act.id)}
        }

    _columns = {
        'name': fields.char('Name', size=128),
        'model_id': fields.many2one('ir.model', 'Object', size=128,
            help="This field is not used, it only helps you to select a good model."),
        'model': fields.char('Object Name', size=128),
        'action_id': fields.many2one('ir.actions.actions', 'Action',
            help="This field is not used, it only helps you to select the right action."),
        'value': fields.text('Value'),
        'value_unpickle': fields.function(_value_unpickle, fnct_inv=_value_pickle,
            method=True, type='text', string='Value'),
        'object': fields.boolean('Is Object'),
        'key': fields.selection([('action','Action'),('default','Default')], 'Type', size=128),
        'key2': fields.char('Event Type', size=256,
            help="The kind of action or button in the client side that will trigger the action."),
        'meta': fields.text('Meta Datas'),
        'meta_unpickle': fields.function(_value_unpickle, fnct_inv=_value_pickle,
            method=True, type='text', string='Metadata'),
        'res_id': fields.integer('Object ID', help="Keep 0 if the action must appear on all resources."),
        'user_id': fields.many2one('res.users', 'User', ondelete='cascade'),
        'company_id': fields.many2one('res.company', 'Company')
    }
    _defaults = {
        'key': lambda *a: 'action',
        'key2': lambda *a: 'tree_but_open',
        'company_id': lambda *a: False
    }

    def _auto_init(self, cr, context={}):
        super(ir_values, self)._auto_init(cr, context)
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = \'ir_values_key_model_key2_index\'')
        if not cr.fetchone():
            cr.execute('CREATE INDEX ir_values_key_model_key2_index ON ir_values (key, model, key2)')
            cr.commit()

    def set(self, cr, uid, key, key2, name, models, value, replace=True, isobject=False, meta=False, preserve_user=False, company=False):
        if type(value)==type(u''):
            value = value.encode('utf8')
        if not isobject:
            value = pickle.dumps(value)
        if meta:
            meta = pickle.dumps(meta)
        ids_res = []
        for model in models:
            if type(model)==type([]) or type(model)==type(()):
                model,res_id = model
            else:
                res_id=False
            if replace:
                if key in ('meta', 'default'):
                    ids = self.search(cr, uid, [
                        ('key', '=', key),
                        ('key2', '=', key2),
                        ('name', '=', name),
                        ('model', '=', model),
                        ('res_id', '=', res_id),
                        ('user_id', '=', preserve_user and uid)
                        ])
                else:
                    ids = self.search(cr, uid, [
                        ('key', '=', key),
                        ('key2', '=', key2),
                        ('value', '=', value),
                        ('model', '=', model),
                        ('res_id', '=', res_id),
                        ('user_id', '=', preserve_user and uid)
                        ])
                self.unlink(cr, uid, ids)
            vals = {
                'name': name,
                'value': value,
                'model': model,
                'object': isobject,
                'key': key,
                'key2': key2 and key2[:200],
                'meta': meta,
                'user_id': preserve_user and uid,
            }
            if company:
                cid = self.pool.get('res.users').browse(cr, uid, uid, context={}).company_id.id
                vals['company_id']=cid
            if res_id:
                vals['res_id']= res_id
            ids_res.append(self.create(cr, uid, vals))
        return ids_res

    def get(self, cr, uid, key, key2, models, meta=False, context={}, res_id_req=False, without_user=True, key2_req=True):
        result = []
        for m in models:
            if type(m)==type([]) or type(m)==type(()):
                m,res_id = m
            else:
                res_id=False

            where = ['key=%s','model=%s']
            params = [key, str(m)]
            if key2:
                where.append('key2=%s')
                params.append(key2[:200])
            else:
                if key2_req and not meta:
                    where.append('key2 is null')

            if res_id_req and (models[-1][0]==m):
                if res_id:
                    where.append('res_id=%s')
                    params.append(res_id)
                else:
                    where.append('(res_id is NULL)')
            elif res_id:
                if (models[-1][0]==m):
                    where.append('(res_id=%s or (res_id is null))')
                    params.append(res_id)
                else:
                    where.append('res_id=%s')
                    params.append(res_id)

            where.append('(user_id=%s or (user_id IS NULL))')
            params.append(uid)

            clause = ' and '.join(where)
            cr.execute('select id,name,value,object,meta, key from ir_values where ' + clause, params)
            result = cr.fetchall()
            if result:
                break

        if not result:
            return []

        def _result_get(x, keys):
            if x[1] in keys:
                return False
            keys.append(x[1])
            if x[3]:
                model,id = x[2].split(',')
                id = int(id)
                fields = self.pool.get(model).fields_get_keys(cr, uid)
                pos = 0
                while pos<len(fields):
                    if fields[pos] in ('report_sxw_content', 'report_rml_content',
                        'report_sxw', 'report_rml', 'report_sxw_content_data',
                        'report_rml_content_data'):
                        del fields[pos]
                    else:
                        pos+=1
                try:
                    datas = self.pool.get(model).read(cr, uid, [id], fields, context)
                except except_orm:
                    return False
                datas= datas and datas[0] or None
                if not datas:
                    #ir_del(cr, uid, x[0])
                    return False
            else:
                datas = pickle.loads(str(x[2].encode('utf-8')))
            if meta:
                meta2 = pickle.loads(x[4])
                return (x[0],x[1],datas,meta2)
            return (x[0],x[1],datas)
        keys = []
        res = filter(bool, map(lambda x: _result_get(x, keys), list(result)))
        res2 = res[:]
        for r in res:
            if type(r[2])==type({}) and 'type' in r[2]:
                if r[2]['type'] in ('ir.actions.report.xml','ir.actions.act_window','ir.actions.wizard'):
                    groups = r[2].get('groups_id')
                    if groups:
                        cr.execute('SELECT COUNT(1) FROM res_groups_users_rel WHERE gid in %s and uid=%s',
                                   (tuple(groups), uid)
                                  )
                        cnt = cr.fetchone()[0]
                        if cnt:
                            res2.remove(r)
                        if r[1] == 'Menuitem' and not res2:
                            raise osv.except_osv('Error !','You do not have the permission to perform this operation !!!')

        return res2
ir_values()



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

