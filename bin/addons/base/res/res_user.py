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

from osv import fields,osv
from osv.orm import browse_record
import tools
from functools import partial
import pytz
import pooler
from tools.translate import _
from service import security
import netsvc

class groups(osv.osv):
    _name = "res.groups"
    _order = 'name'
    _columns = {
        'name': fields.char('Group Name', size=64, required=True),
        'model_access': fields.one2many('ir.model.access', 'group_id', 'Access Controls'),
        'rule_groups': fields.many2many('ir.rule', 'rule_group_rel',
            'group_id', 'rule_group_id', 'Rules', domain="[('global', '<>', True)]"),
        'menu_access': fields.many2many('ir.ui.menu', 'ir_ui_menu_group_rel', 'gid', 'menu_id', 'Access Menu'),
        'comment' : fields.text('Comment',size=250),
    }
    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'The name of the group must be unique !')
    ]

    def copy(self, cr, uid, id, default=None, context={}):
        group_name = self.read(cr, uid, [id], ['name'])[0]['name']
        default.update({'name': group_name +' (copy)'})
        return super(groups, self).copy(cr, uid, id, default, context)

    def write(self, cr, uid, ids, vals, context=None):
        if 'name' in vals:
            if vals['name'].startswith('-'):
                raise osv.except_osv(_('Error'),
                        _('The name of the group can not start with "-"'))
        res = super(groups, self).write(cr, uid, ids, vals, context=context)
        self.pool.get('ir.model.access').call_cache_clearing_methods(cr)
        return res

    def create(self, cr, uid, vals, context=None):
        if 'name' in vals:
            if vals['name'].startswith('-'):
                raise osv.except_osv(_('Error'),
                        _('The name of the group can not start with "-"'))
        gid = super(groups, self).create(cr, uid, vals, context=context)
        if context and context.get('noadmin', False):
            pass
        else:
            # assign this new group to user_root
            user_obj = self.pool.get('res.users')
            aid = user_obj.browse(cr, 1, user_obj._get_admin_id(cr))
            if aid:
                aid.write({'groups_id': [(4, gid)]})
        return gid

    def copy(self, cr, uid, id, default={}, context={}, done_list=[], local=False):
        group = self.browse(cr, uid, id, context=context)
        default = default.copy()
        if not 'name' in default:
            default['name'] = group['name']
        default['name'] = default['name'] + _(' (copy)')
        return super(groups, self).copy(cr, uid, id, default, context=context)

    def get_extended_interface_group(self, cr, uid, context=None):
        data_obj = self.pool.get('ir.model.data')
        extended_group_data_id = data_obj._get_id(cr, uid, 'base', 'group_extended')
        return data_obj.browse(cr, uid, extended_group_data_id, context=context).res_id

groups()

class roles(osv.osv):
    _name = "res.roles"
    _columns = {
        'name': fields.char('Role Name', size=64, required=True),
        'parent_id': fields.many2one('res.roles', 'Parent', select=True),
        'child_id': fields.one2many('res.roles', 'parent_id', 'Children'),
        'users': fields.many2many('res.users', 'res_roles_users_rel', 'rid', 'uid', 'Users'),
    }
    _defaults = {
    }
    def check(self, cr, uid, ids, role_id):
        if role_id in ids:
            return True
        cr.execute('select parent_id from res_roles where id=%s', (role_id,))
        roles = cr.fetchone()[0]
        if roles:
            return self.check(cr, uid, ids, roles)
        return False
roles()

def _lang_get(self, cr, uid, context={}):
    obj = self.pool.get('res.lang')
    ids = obj.search(cr, uid, [('translatable','=',True)])
    res = obj.read(cr, uid, ids, ['code', 'name'], context)
    res = [(r['code'], r['name']) for r in res]
    return res

def _tz_get(self,cr,uid, context={}):
    return [(x, x) for x in pytz.all_timezones]

class users(osv.osv):
    __admin_ids = {}
    _uid_cache = {}
    _name = "res.users"

    WELCOME_MAIL_SUBJECT = u"Welcome to OpenERP"
    WELCOME_MAIL_BODY = u"An OpenERP account has been created for you, "\
        "\"%(name)s\".\n\nYour login is %(login)s, "\
        "you should ask your supervisor or system administrator if you "\
        "haven't been given your password yet.\n\n"\
        "If you aren't %(name)s, this email reached you errorneously, "\
        "please delete it."

    def get_welcome_mail_subject(self, cr, uid, context=None):
        """ Returns the subject of the mail new users receive (when
        created via the res.config.users wizard), default implementation
        is to return config_users.WELCOME_MAIL_SUBJECT
        """
        return self.WELCOME_MAIL_SUBJECT
    def get_welcome_mail_body(self, cr, uid, context=None):
        """ Returns the subject of the mail new users receive (when
        created via the res.config.users wizard), default implementation
        is to return config_users.WELCOME_MAIL_BODY
        """
        return self.WELCOME_MAIL_BODY

    def get_current_company(self, cr, uid):
        res=[]
        cr.execute('select company_id, res_company.name from res_users left join res_company on res_company.id = company_id where res_users.id=%s' %uid)
        res = cr.fetchall()
        return res

    def send_welcome_email(self, cr, uid, id, context=None):
        logger= netsvc.Logger()
        user = self.pool.get('res.users').read(cr, uid, id, context=context)
        if not tools.config.get('smtp_server'):
            logger.notifyChannel('mails', netsvc.LOG_WARNING,
                _('"smtp_server" needs to be set to send mails to users'))
            return False
        if not tools.config.get('email_from'):
            logger.notifyChannel("mails", netsvc.LOG_WARNING,
                _('"email_from" needs to be set to send welcome mails '
                  'to users'))
            return False
        if not user.get('email'):
            return False

        return tools.email_send(email_from=None, email_to=[user['email']],
                                subject=self.get_welcome_mail_subject(
                                    cr, uid, context=context),
                                body=self.get_welcome_mail_body(
                                    cr, uid, context=context) % user)

    def _set_interface_type(self, cr, uid, ids, name, value, arg, context=None):
        """Implementation of 'view' function field setter, sets the type of interface of the users.
        @param name: Name of the field
        @param arg: User defined argument
        @param value: new value returned
        @return:  True/False
        """
        if not value or value not in ['simple','extended']:
            return False
        group_obj = self.pool.get('res.groups')
        extended_group_id = group_obj.get_extended_interface_group(cr, uid, context=context)
        if type(ids) in (int,long,):
            ids = [ids]
        if value != 'simple':
            #To avoid insert duplication extended group
            for user in self.browse(cr, uid, ids, context=context):
                group_ids = map(lambda x:x.id, user.groups_id)
                if extended_group_id not in group_ids:
                    self.write(cr, uid, [user.id], {'groups_id': [(4, extended_group_id)]}, context=context)
        else:
            self.write(cr, uid, ids, {'groups_id': [(3, extended_group_id)]}, context=context)
        return True


    def _get_interface_type(self, cr, uid, ids, name, args, context=None):
        """Implementation of 'view' function field getter, returns the type of interface of the users.
        @param field_name: Name of the field
        @param arg: User defined argument
        @return:  Dictionary of values
        """
        group_obj = self.pool.get('res.groups')
        extended_group_id = group_obj.get_extended_interface_group(cr, uid, context=context)
        extended_users = group_obj.read(cr, uid, extended_group_id, ['users'], context=context)['users']
        return dict(zip(ids, ['extended' if user in extended_users else 'simple' for user in ids]))

    def _email_get(self, cr, uid, ids, name, arg, context=None):
        return dict([(user.id, user.address_id.email) for user in self.browse(cr, uid, ids, context=context)])

    def _email_set(self, cr, uid, ids, name, value, arg, context=None):
        if not isinstance(ids,list):
            ids = [ids]
        address_obj = self.pool.get('res.partner.address')
        for user in self.browse(cr, uid, ids, context=context):
            if user.address_id:
                address_obj.write(cr, 1, user.address_id.id, {'email': value or None}) # no context to avoid potential security issues as superuser
            else:
                address_id = address_obj.create(cr, 1, {'name': user.name, 'email': value or None}) # no context to avoid potential security issues as superuser
                self.write(cr, uid, ids, {'address_id': address_id}, context)
        return True

    _columns = {
        'name': fields.char('Name', size=64, required=True, select=True,
                            help="The new user's real name, used for searching"
                                 " and most listings"),
        'login': fields.char('Login', size=64, required=True,
                             help="Used to log into the system"),
        'password': fields.char('Password', size=64, invisible=True, help="Keep empty if you don't want the user to be able to connect on the system."),
        'email': fields.char('E-mail', size=64,
            help='If an email is provided, the user will be sent a message '
                 'welcoming him.\n\nWarning: if "email_from" and "smtp_server"'
                 " aren't configured, it won't be possible to email new "
                 "users."),
        'signature': fields.text('Signature', size=64),
        'address_id': fields.many2one('res.partner.address', 'Address'),
        'active': fields.boolean('Active'),
        'action_id': fields.many2one('ir.actions.actions', 'Home Action'),
        'menu_id': fields.many2one('ir.actions.actions', 'Menu Action'),
        'groups_id': fields.many2many('res.groups', 'res_groups_users_rel', 'uid', 'gid', 'Groups'),
        'roles_id': fields.many2many('res.roles', 'res_roles_users_rel', 'uid', 'rid', 'Roles'),

        # Special behavior for this field: res.company.search() will only return the companies
        # available to the current user (should be the user's companies?), when the user_preference
        # context is set.
        'company_id': fields.many2one('res.company', 'Company', required=True,
            help="The company this user is currently working for.", context={'user_preference': True}),

        'company_ids':fields.many2many('res.company','res_company_users_rel','user_id','cid','Companies'),
        'context_lang': fields.selection(_lang_get, 'Language', required=True,
            help="Sets the language for the user's user interface, when UI "
                 "translations are available"),
        'context_tz': fields.selection(_tz_get,  'Timezone', size=64,
            help="The user's timezone, used to perform timezone conversions "
                 "between the server and the client."),
        'view': fields.function(_get_interface_type, method=True, type='selection', fnct_inv=_set_interface_type,
                                selection=[('simple','Simplified'),('extended','Extended')],
                                string='Interface', help="Choose between the simplified interface and the extended one"),
        'user_email': fields.function(_email_get, method=True, fnct_inv=_email_set, string='Email', type="char", size=240),
    }

    def read(self,cr, uid, ids, fields=None, context=None, load='_classic_read'):
        def override_password(o):
            if 'password' in o and ( 'id' not in o or o['id'] != uid ):
                o['password'] = '********'
            return o

        result = super(users, self).read(cr, uid, ids, fields, context, load)
        canwrite = self.pool.get('ir.model.access').check(cr, uid, 'res.users', 'write', raise_exception=False)
        if not canwrite:
            if isinstance(ids, (int, float)):
                result = override_password(result)
            else:
                result = map(override_password, result)

        if isinstance(result, list):
            for rec in result:
                if not rec.get('action_id',True):
                    rec['action_id'] = (self._get_menu(cr, uid),'Menu')
        else:
            if not result.get('action_id',True):
                result['action_id'] = (self._get_menu(cr, uid),'Menu')

        return result


    def _check_company(self, cr, uid, ids, context=None):
        return all(((this.company_id in this.company_ids) or not this.company_ids) for this in self.browse(cr, uid, ids, context))

    _constraints = [
        (_check_company, 'The chosen company is not in the allowed companies for this user', ['company_id', 'company_ids']),
    ]

    _sql_constraints = [
        ('login_key', 'UNIQUE (login)',  _('You can not have two users with the same login !'))
    ]

    def _get_email_from(self, cr, uid, ids, context=None):
        if not isinstance(ids, list):
            ids = [ids]
        res = dict.fromkeys(ids)
        for user in self.browse(cr, uid, ids, context=context):
            if user.user_email:
                res[user.id] = "%s <%s>" % (user.name, user.user_email)
        return res

    def _get_admin_id(self, cr):
        if self.__admin_ids.get(cr.dbname) is None:
            ir_model_data_obj = self.pool.get('ir.model.data')
            mdid = ir_model_data_obj._get_id(cr, 1, 'base', 'user_root')
            self.__admin_ids[cr.dbname] = ir_model_data_obj.read(cr, 1, [mdid], ['res_id'])[0]['res_id']
        return self.__admin_ids[cr.dbname]

    def _get_action(self,cr, uid, context={}):
        ids = self.pool.get('ir.ui.menu').search(cr, uid, [('usage','=','menu')])
        return ids and ids[0] or False

    def _get_company(self,cr, uid, context=None, uid2=False):
        if not uid2:
            uid2 = uid
        user = self.pool.get('res.users').read(cr, uid, uid2, ['company_id'], context)
        company_id = user.get('company_id', False)
        return company_id and company_id[0] or False

    def _get_companies(self, cr, uid, context=None):
        c = self._get_company(cr, uid, context)
        if c:
            return [c]
        return False

    def _get_menu(self,cr, uid, context={}):
        ids = self.pool.get('ir.actions.act_window').search(cr, uid, [('usage','=','menu')])
        return ids and ids[0] or False

    def _get_group(self,cr, uid, context={}):
        ids = self.pool.get('res.groups').search(cr, uid, [('name','=','Employee')])
        return ids or False

    _defaults = {
        'password' : lambda *a : '',
        'context_lang': lambda *args: 'en_US',
        'active' : lambda *a: True,
        'menu_id': _get_menu,
        'action_id': _get_menu,
        'company_id': _get_company,
        'company_ids': _get_companies,
        'groups_id': _get_group,
        'address_id': False,
    }

    @tools.cache()
    def company_get(self, cr, uid, uid2, context=None):
        return self._get_company(cr, uid, context=context, uid2=uid2)

    def write(self, cr, uid, ids, values, context=None):
        if not hasattr(ids, '__iter__'):
            ids = [ids]
        if ids == [uid]:
            for key in values.keys():
                if not (key in ('view', 'password','signature','action_id', 'company_id') or key.startswith('context_')):
                    break
            else:
                uid = 1
        res = super(users, self).write(cr, uid, ids, values, context=context)

        # clear caches linked to the users
        self.company_get.clear_cache(cr.dbname)
        self.pool.get('ir.model.access').call_cache_clearing_methods(cr)
        clear = partial(self.pool.get('ir.rule').clear_cache, cr)
        map(clear, ids)

        return res

    def unlink(self, cr, uid, ids, context=None):
        if 1 in ids:
            raise osv.except_osv(_('Can not remove root user!'), _('You can not remove the admin user as it is used internally for resources created by OpenERP (updates, module installation, ...)'))
        return super(users, self).unlink(cr, uid, ids, context=context)

    def name_search(self, cr, user, name='', args=None, operator='ilike', context=None, limit=100):
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

    def context_get(self, cr, uid, context=None):
        user = self.browse(cr, uid, uid, context)
        result = {}
        for k in self._columns.keys():
            if k.startswith('context_'):
                res = getattr(user,k) or False
                if isinstance(res, browse_record):
                    res = res.id
                result[k[8:]] = res or False
        return result

    def action_get(self, cr, uid, context={}):
        dataobj = self.pool.get('ir.model.data')
        data_id = dataobj._get_id(cr, 1, 'base', 'action_res_users_my')
        return dataobj.browse(cr, uid, data_id, context).res_id


    def login(self, db, login, password):
        if not password:
            return False
        cr = pooler.get_db(db).cursor()
        cr.execute('select id from res_users where login=%s and password=%s and active', (tools.ustr(login), tools.ustr(password)))
        res = cr.fetchone()
        cr.close()
        if res:
            return res[0]
        else:
            return False

    def check_super(self, passwd):
        if passwd == tools.config['admin_passwd']:
            return True
        else:
            raise security.ExceptionNoTb('AccessDenied')

    def check(self, db, uid, passwd):
        if not passwd:
            return False
        cached_pass = self._uid_cache.get(db, {}).get(uid)
        if (cached_pass is not None) and cached_pass == passwd:
            return True
        cr = pooler.get_db(db).cursor()
        cr.execute('select count(1) from res_users where id=%s and password=%s and active=%s', (int(uid), passwd, True))
        res = cr.fetchone()[0]
        cr.close()
        if not bool(res):
            raise security.ExceptionNoTb('AccessDenied')
        if res:
            if self._uid_cache.has_key(db):
                ulist = self._uid_cache[db]
                ulist[uid] = passwd
            else:
                self._uid_cache[db] = {uid:passwd}
        return bool(res)

    def access(self, db, uid, passwd, sec_level, ids):
        if not passwd:
            return False
        cr = pooler.get_db(db).cursor()
        cr.execute('select id from res_users where id=%s and password=%s', (uid, passwd))
        res = cr.fetchone()
        cr.close()
        if not res:
            raise security.ExceptionNoTb('Bad username or password')
        return res[0]

users()

class config_users(osv.osv_memory):
    _name = 'res.config.users'
    _inherit = ['res.users', 'res.config']

    def _generate_signature(self, cr, name, email, context=None):
        return _('--\n%(name)s %(email)s\n') % {
            'name': name or '',
            'email': email and ' <'+email+'>' or '',
            }

    def create_user(self, cr, uid, new_id, context=None):
        """ create a new res.user instance from the data stored
        in the current res.config.users.

        If an email address was filled in for the user, sends a mail
        composed of the return values of ``get_welcome_mail_subject``
        and ``get_welcome_mail_body`` (which should be unicode values),
        with the user's data %-formatted into the mail body
        """
        base_data = self.read(cr, uid, new_id, context=context)
        partner_id = self.pool.get('res.partner').main_partner(cr, uid)
        address = self.pool.get('res.partner.address').create(
            cr, uid, {'name': base_data['name'],
                      'email': base_data['email'],
                      'partner_id': partner_id,},
            context)
        user_data = dict(
            base_data,
            signature=self._generate_signature(
                cr, base_data['name'], base_data['email'], context=context),
            address_id=address,
            )
        new_user = self.pool.get('res.users').create(
            cr, uid, user_data, context)
        self.send_welcome_email(cr, uid, new_user, context=context)
    def execute(self, cr, uid, ids, context=None):
        'Do nothing on execution, just launch the next action/todo'
        pass
    def action_add(self, cr, uid, ids, context=None):
        'Create a user, and re-display the view'
        self.create_user(cr, uid, ids[0], context=context)
        return {
            'view_type': 'form',
            "view_mode": 'form',
            'res_model': 'res.config.users',
            'view_id':self.pool.get('ir.ui.view')\
                .search(cr,uid,[('name','=','res.config.users.confirm.form')]),
            'type': 'ir.actions.act_window',
            'target':'new',
            }
config_users()

class groups2(osv.osv): ##FIXME: Is there a reason to inherit this object ?
    _inherit = 'res.groups'
    _columns = {
        'users': fields.many2many('res.users', 'res_groups_users_rel', 'gid', 'uid', 'Users'),
    }

    def unlink(self, cr, uid, ids, context=None):
        for record in self.read(cr, uid, ids, ['users'], context=context):
            if record['users']:
                raise osv.except_osv(_('Warning !'), _('Make sure you have no users linked with the group(s)!'))
        return super(groups2, self).unlink(cr, uid, ids, context=context)

groups2()

class res_config_view(osv.osv_memory):
    _name = 'res.config.view'
    _inherit = 'res.config'
    _columns = {
        'name':fields.char('Name', size=64),
        'view': fields.selection([('simple','Simplified'),
                                  ('extended','Extended')],
                                 'Interface', required=True ),
    }
    _defaults={
        'view':lambda *args: 'simple',
    }

    def execute(self, cr, uid, ids, context=None):
        res = self.read(cr, uid, ids)[0]
        self.pool.get('res.users').write(cr, uid, [uid],
                                 {'view':res['view']}, context=context)

res_config_view()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

