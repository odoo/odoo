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
from osv.orm import except_orm
import tools
import pytz

class groups(osv.osv):
    _name = "res.groups"
    _columns = {
        'name': fields.char('Group Name', size=64, required=True),
        'model_access': fields.one2many('ir.model.access', 'group_id', 'Access Controls'),
        'rule_groups': fields.many2many('ir.rule.group', 'group_rule_group_rel',
            'group_id', 'rule_group_id', 'Rules', domain="[('global', '<>', True)]"),
        'menu_access': fields.many2many('ir.ui.menu', 'ir_ui_menu_group_rel', 'gid', 'menu_id', 'Access Menu'),
        'comment' : fields.text('Comment',size=250),
    }
    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'The name of the group must be unique !')
    ]

    def write(self, cr, uid, ids, vals, context=None):
        if 'name' in vals:
            if vals['name'].startswith('-'):
                raise osv.except_osv(_('Error'),
                        _('The name of the group can not start with "-"'))
        res = super(groups, self).write(cr, uid, ids, vals, context=context)
        # Restart the cache on the company_get method
        self.pool.get('ir.rule').domain_get()
        return res

    def create(self, cr, uid, vals, context=None):
        if 'name' in vals:
            if vals['name'].startswith('-'):
                raise osv.except_osv(_('Error'),
                        _('The name of the group can not start with "-"'))
        return super(groups, self).create(cr, uid, vals, context=context)

groups()


class roles(osv.osv):
    _name = "res.roles"
    _columns = {
        'name': fields.char('Role Name', size=64, required=True),
        'parent_id': fields.many2one('res.roles', 'Parent', select=True),
        'child_id': fields.one2many('res.roles', 'parent_id', 'Childs'),
        'users': fields.many2many('res.users', 'res_roles_users_rel', 'rid', 'uid', 'Users'),
        'groups': fields.many2many('res.groups', 'res_roles_groups_rel', 'rid', 'gid', 'Groups'),
    }
    _defaults = {
    }
    def check(self, cr, uid, ids, role_id):
        if role_id in ids:
            return True
        cr.execute('select parent_id from res_roles where id=%d', (role_id,))
        roles = cr.fetchone()[0]
        if roles:
            return self.check(cr, uid, ids, roles)
        return False
roles()

def _lang_get(self, cr, uid, context={}):
    obj = self.pool.get('res.lang')
    ids = obj.search(cr, uid, [])
    res = obj.read(cr, uid, ids, ['code', 'name'], context)
    res = [(r['code'], r['name']) for r in res]
    return res
def _tz_get(self,cr,uid, context={}):
    return [(x, x) for x in pytz.all_timezones]

class users(osv.osv):
    _name = "res.users"
    _log_access = False
    _columns = {
        'name': fields.char('Name', size=64, required=True, select=True),
        'login': fields.char('Login', size=64, required=True),
        'password': fields.char('Password', size=64, invisible=True),
        'signature': fields.text('Signature', size=64),
        'address_id': fields.many2one('res.partner.address', 'Address'),
        'active': fields.boolean('Active'),
        'action_id': fields.many2one('ir.actions.actions', 'Home Action'),
        'menu_id': fields.many2one('ir.actions.actions', 'Menu Action'),
        'groups_id': fields.many2many('res.groups', 'res_groups_users_rel', 'uid', 'gid', 'Groups'),
        'roles_id': fields.many2many('res.roles', 'res_roles_users_rel', 'uid', 'rid', 'Roles'),
        'rules_id': fields.many2many('ir.rule.group', 'user_rule_group_rel', 'user_id', 'rule_group_id', 'Rules'),
        'company_id': fields.many2one('res.company', 'Company'),
        'context_lang': fields.selection(_lang_get, 'Language', required=True),
        'context_tz': fields.selection(_tz_get,  'Timezone', size=64)
    }
    _sql_constraints = [
        ('login_key', 'UNIQUE (login)', 'You can not have two users with the same login !')
    ]
    def _get_action(self,cr, uid, context={}):
        ids = self.pool.get('ir.ui.menu').search(cr, uid, [('usage','=','menu')])
        return ids and ids[0] or False

    def _get_company(self,cr, uid, context={}):
        return self.pool.get('res.users').browse(cr, uid, uid, context).company_id.id

    def _get_menu(self,cr, uid, context={}):
        ids = self.pool.get('ir.actions.act_window').search(cr, uid, [('usage','=','menu')])
        return ids and ids[0] or False

    _defaults = {
        'password' : lambda obj,cr,uid,context={} : '',
        'context_lang': lambda *args: 'en_US',
        'active' : lambda obj,cr,uid,context={} : True,
        'menu_id': _get_menu,
        'action_id': _get_menu,
        'company_id': _get_company,
    }
    def company_get(self, cr, uid, uid2):
        company_id = self.pool.get('res.users').browse(cr, uid, uid).company_id.id
        return company_id
    company_get = tools.cache()(company_get)

    def write(self, cr, uid, ids, values, *args, **argv):
        ok = False
        res = {}
        if (ids == [uid]):
            for k in values.keys():
                if k in ('password', 'signature', 'action_id', 'context_lang', 'context_tz'):
                    ok=True
        if ok or uid==1:
            res = super(users, self).write(cr, uid, ids, values, *args, **argv)
            self.company_get()
            # Restart the cache on the company_get method
            self.pool.get('ir.rule').domain_get()
        else:
            raise except_orm(_('AccessError'), 'You can not write in this document (res.users)')
        return res

    def read(self,cr, uid, ids, fields=None, context=None, load='_classic_read'):
        result = super(users, self).read(cr, uid, ids, fields, context, load)
        #canwrite = self.pool.get('ir.model.access').check(cr, uid, 'res.users', 'write', raise_exception=False)
        #if not canwrite and ids!=[uid]:
        #    for r in result:
        #        if 'password' in r:
        #            r['password'] = '********'
        #    result=r
        return result

    def unlink(self, cr, uid, ids):
        if 1 in ids:
            raise osv.except_osv(_('Can not remove root user!'), _('You can not remove the root user as it is used internally for resources created by Open ERP (updates, module installation, ...)'))
        return super(users, self).unlink(cr, uid, ids)

    def name_search(self, cr, user, name='', args=None, operator='ilike', context=None, limit=80):
        if not args:
            args=[]
        if not context:
            context={}
        ids = []
        if name:
            ids = self.search(cr, user, [('login','=',name)]+ args, limit=limit)
        if not ids:
            ids = self.search(cr, user, [('name',operator,name)]+ args, limit=limit)
        return self.name_get(cr, user, ids)

    def copy(self, cr, uid, id, default=None, context={}):
        login = self.read(cr, uid, [id], ['login'])[0]['login']
        default.update({'login': login+' (copy)'})
        return super(users, self).copy(cr, uid, id, default, context)

    def context_get(self, cr, uid, context={}):
        user = self.browse(cr, uid, uid, context)
        result = {}
        for k in self._columns.keys():
            if k.startswith('context_'):
                result[k[8:]] = getattr(user,k)
        return result

    def action_get(self, cr, uid, context={}):
        dataobj = self.pool.get('ir.model.data')
        data_id = dataobj._get_id(cr, 1, 'base', 'action_res_users_my')
        return dataobj.browse(cr, uid, data_id, context).res_id

    def action_next(self,cr,uid,ids,context=None):
        return{
                'view_type': 'form',
                "view_mode": 'form',
                'res_model': 'ir.module.module.configuration.wizard',
                'type': 'ir.actions.act_window',
                'target':'new',
        }

    def action_continue(self,cr,uid,ids,context={}):
        return {
                'view_type': 'form',
                "view_mode": 'form',
                'res_model': 'ir.module.module.configuration.wizard',
                'type': 'ir.actions.act_window',
                'target':'new',
               }
    def action_new(self,cr,uid,ids,context={}):
        return {
                'view_type': 'form',
                "view_mode": 'form',
                'res_model': 'res.users',
                'view_id':self.pool.get('ir.ui.view').search(cr,uid,[('name','=','res.users.confirm.form')]),
                'type': 'ir.actions.act_window',
                'target':'new',
               }
    
    def action_cancel(self,cr,uid,ids,conect={}):
        return {
            'view_type': 'form',
            "view_mode": 'form',
            'res_model': 'ir.module.module.configuration.wizard',
            'type': 'ir.actions.act_window',
            'target':'new',
        }
users()

class groups2(osv.osv): ##FIXME: Is there a reason to inherit this object ?
    _inherit = 'res.groups'
    _columns = {
        'users': fields.many2many('res.users', 'res_groups_users_rel', 'gid', 'uid', 'Users'),
        'roles': fields.many2many('res.roles', 'res_roles_groups_rel', 'gid', 'rid', 'Roles'),
    }
groups2()


class res_config_view(osv.osv_memory):
    _name='res.config.view'
    _columns = {
        'name':fields.char('Name', size=64),
        'view': fields.selection([('simple','Simple'),('extended','Extended')], 'View', required=True ),

    }
    _defaults={
        'view':lambda *args: 'simple',
        }

    def action_cancel(self,cr,uid,ids,conect=None):
        print ' Cancel  action'
        return {
                'view_type': 'form',
                "view_mode": 'form',
                'res_model': 'ir.module.module.configuration.wizard',
                'type': 'ir.actions.act_window',
                'target':'new',
         }
    def action_set(self, cr, uid, ids, context=None):
        res=self.read(cr,uid,ids)[0]
        users_obj = self.pool.get('res.users')
        group_obj=self.pool.get('res.groups')
        if 'view' in res and res['view'] and res['view']=='extended':
            group_ids=group_obj.search(cr,uid,[('name','=','Extended View')])
            if group_ids and len(group_ids):
                users_obj.write(cr, uid, [3],{
                                'groups_id':[(4,group_ids[0])]
                            }, context=context)
        return {
                'view_type': 'form',
                "view_mode": 'form',
                'res_model': 'ir.module.module.configuration.wizard',
                'type': 'ir.actions.act_window',
                'target':'new',
            }

res_config_view()
