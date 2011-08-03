# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#    Copyright (C) 2010-2011 OpenERP s.a. (<http://openerp.com>).
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
import logging
from lxml import etree

class groups(osv.osv):
    _name = "res.groups"
    _order = 'name'
    _description = "Access Groups"
    _columns = {
        'name': fields.char('Group Name', size=64, required=True, translate=True),
        'users': fields.many2many('res.users', 'res_groups_users_rel', 'gid', 'uid', 'Users'),
        'model_access': fields.one2many('ir.model.access', 'group_id', 'Access Controls'),
        'rule_groups': fields.many2many('ir.rule', 'rule_group_rel',
            'group_id', 'rule_group_id', 'Rules', domain=[('global', '=', False)]),
        'menu_access': fields.many2many('ir.ui.menu', 'ir_ui_menu_group_rel', 'gid', 'menu_id', 'Access Menu'),
        'comment' : fields.text('Comment',size=250),
    }
    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'The name of the group must be unique !')
    ]

    def copy(self, cr, uid, id, default=None, context=None):
        group_name = self.read(cr, uid, [id], ['name'])[0]['name']
        default.update({'name': _('%s (copy)')%group_name})
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

    def unlink(self, cr, uid, ids, context=None):
        group_users = []
        for record in self.read(cr, uid, ids, ['users'], context=context):
            if record['users']:
                group_users.extend(record['users'])
        if group_users:
            user_names = [user.name for user in self.pool.get('res.users').browse(cr, uid, group_users, context=context)]
            user_names = list(set(user_names))
            if len(user_names) >= 5:
                user_names = user_names[:5] + ['...']
            raise osv.except_osv(_('Warning !'),
                        _('Group(s) cannot be deleted, because some user(s) still belong to them: %s !') % \
                            ', '.join(user_names))
        return super(groups, self).unlink(cr, uid, ids, context=context)

    def get_extended_interface_group(self, cr, uid, context=None):
        data_obj = self.pool.get('ir.model.data')
        extended_group_data_id = data_obj._get_id(cr, uid, 'base', 'group_extended')
        return data_obj.browse(cr, uid, extended_group_data_id, context=context).res_id

groups()

def _lang_get(self, cr, uid, context=None):
    obj = self.pool.get('res.lang')
    ids = obj.search(cr, uid, [('translatable','=',True)])
    res = obj.read(cr, uid, ids, ['code', 'name'], context=context)
    res = [(r['code'], r['name']) for r in res]
    return res

def _tz_get(self,cr,uid, context=None):
    return [(x, x) for x in pytz.all_timezones]

class users(osv.osv):
    __admin_ids = {}
    _uid_cache = {}
    _name = "res.users"
    _order = 'name'

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
        cr.execute('select company_id, res_company.name from res_users left join res_company on res_company.id = company_id where res_users.id=%s' %uid)
        return cr.fetchall()

    def send_welcome_email(self, cr, uid, id, context=None):
        logger= netsvc.Logger()
        user = self.pool.get('res.users').read(cr, uid, id, context=context)
        if not user.get('email'):
            return False
        if not tools.config.get('smtp_server'):
            logger.notifyChannel('mails', netsvc.LOG_WARNING,
                _('"smtp_server" needs to be set to send mails to users'))
            return False
        if not tools.config.get('email_from'):
            logger.notifyChannel("mails", netsvc.LOG_WARNING,
                _('"email_from" needs to be set to send welcome mails '
                  'to users'))
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
        # First always remove the users from the group (avoids duplication if called twice)
        self.write(cr, uid, ids, {'groups_id': [(3, extended_group_id)]}, context=context)
        # Then add them back if requested
        if value == 'extended':
            self.write(cr, uid, ids, {'groups_id': [(4, extended_group_id)]}, context=context)
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
        # perform this as superuser because the current user is allowed to read users, and that includes
        # the email, even without any direct read access on the res_partner_address object.
        return dict([(user.id, user.address_id.email) for user in self.browse(cr, 1, ids)]) # no context to avoid potential security issues as superuser

    def _email_set(self, cr, uid, ids, name, value, arg, context=None):
        if not isinstance(ids,list):
            ids = [ids]
        address_obj = self.pool.get('res.partner.address')
        for user in self.browse(cr, uid, ids, context=context):
            # perform this as superuser because the current user is allowed to write to the user, and that includes
            # the email even without any direct write access on the res_partner_address object.
            if user.address_id:
                address_obj.write(cr, 1, user.address_id.id, {'email': value or None}) # no context to avoid potential security issues as superuser
            else:
                address_id = address_obj.create(cr, 1, {'name': user.name, 'email': value or None}) # no context to avoid potential security issues as superuser
                self.write(cr, uid, ids, {'address_id': address_id}, context)
        return True

    def _set_new_password(self, cr, uid, id, name, value, args, context=None):
        if value is False:
            # Do not update the password if no value is provided, ignore silently.
            # For example web client submits False values for all empty fields.
            return
        if uid == id:
            # To change their own password users must use the client-specific change password wizard,
            # so that the new password is immediately used for further RPC requests, otherwise the user
            # will face unexpected 'Access Denied' exceptions.
            raise osv.except_osv(_('Operation Canceled'), _('Please use the change password wizard (in User Preferences or User menu) to change your own password.'))
        self.write(cr, uid, id, {'password': value})

    def _get_password(self, cr, uid, ids, arg, karg, context=None):
        return dict.fromkeys(ids, '')

    _columns = {
        'name': fields.char('User Name', size=64, required=True, select=True,
                            help="The new user's real name, used for searching"
                                 " and most listings"),
        'login': fields.char('Login', size=64, required=True,
                             help="Used to log into the system"),
        'password': fields.char('Password', size=64, invisible=True, help="Keep empty if you don't want the user to be able to connect on the system."),
        'new_password': fields.function(_get_password, method=True, type='char', size=64,
                                fnct_inv=_set_new_password,
                                string='Change password', help="Only specify a value if you want to change the user password. "
                                "This user will have to logout and login again!"),
        'email': fields.char('E-mail', size=64,
            help='If an email is provided, the user will be sent a message '
                 'welcoming him.\n\nWarning: if "email_from" and "smtp_server"'
                 " aren't configured, it won't be possible to email new "
                 "users."),
        'signature': fields.text('Signature', size=64),
        'address_id': fields.many2one('res.partner.address', 'Address'),
        'active': fields.boolean('Active'),
        'action_id': fields.many2one('ir.actions.actions', 'Home Action', help="If specified, this action will be opened at logon for this user, in addition to the standard menu."),
        'menu_id': fields.many2one('ir.actions.actions', 'Menu Action', help="If specified, the action will replace the standard menu for this user."),
        'groups_id': fields.many2many('res.groups', 'res_groups_users_rel', 'uid', 'gid', 'Groups'),

        # Special behavior for this field: res.company.search() will only return the companies
        # available to the current user (should be the user's companies?), when the user_preference
        # context is set.
        'company_id': fields.many2one('res.company', 'Company', required=True,
            help="The company this user is currently working for.", context={'user_preference': True}),

        'company_ids':fields.many2many('res.company','res_company_users_rel','user_id','cid','Companies'),
        'context_lang': fields.selection(_lang_get, 'Language', required=True,
            help="The default language used in the graphical user interface, when translations are available. To add a new language, you can use the 'Load an Official Translation' wizard available from the 'Administration' menu."),
        'context_tz': fields.selection(_tz_get,  'Timezone', size=64,
            help="The user's timezone, used to perform timezone conversions "
                 "between the server and the client."),
        'view': fields.function(_get_interface_type, method=True, type='selection', fnct_inv=_set_interface_type,
                                selection=[('simple','Simplified'),('extended','Extended')],
                                string='Interface', help="OpenERP offers a simplified and an extended user interface. If you use OpenERP for the first time we strongly advise you to select the simplified interface, which has less features but is easier to use. You can switch to the other interface from the User/Preferences menu at any time."),
        'user_email': fields.function(_email_get, method=True, fnct_inv=_email_set, string='Email', type="char", size=240),
        'menu_tips': fields.boolean('Menu Tips', help="Check out this box if you want to always display tips on each menu action"),
        'date': fields.datetime('Last Connection', readonly=True),
    }

    def on_change_company_id(self, cr, uid, ids, company_id):
        return {
                'warning' : {
                    'title': _("Company Switch Warning"),
                    'message': _("Please keep in mind that documents currently displayed may not be relevant after switching to another company. If you have unsaved changes, please make sure to save and close all forms before switching to a different company. (You can click on Cancel in the User Preferences now)"),
                }
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
        return result


    def _check_company(self, cr, uid, ids, context=None):
        return all(((this.company_id in this.company_ids) or not this.company_ids) for this in self.browse(cr, uid, ids, context))

    _constraints = [
        (_check_company, 'The chosen company is not in the allowed companies for this user', ['company_id', 'company_ids']),
    ]

    _sql_constraints = [
        ('login_key', 'UNIQUE (login)',  'You can not have two users with the same login !')
    ]

    def _get_email_from(self, cr, uid, ids, context=None):
        if not isinstance(ids, list):
            ids = [ids]
        res = dict.fromkeys(ids, False)
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

    def _get_menu(self,cr, uid, context=None):
        dataobj = self.pool.get('ir.model.data')
        try:
            model, res_id = dataobj.get_object_reference(cr, uid, 'base', 'action_menu_admin')
            if model != 'ir.actions.act_window':
                return False
            return res_id
        except ValueError:
            return False

    def _get_group(self,cr, uid, context=None):
        dataobj = self.pool.get('ir.model.data')
        result = []
        try:
            dummy,group_id = dataobj.get_object_reference(cr, 1, 'base', 'group_user')
            result.append(group_id)
            dummy,group_id = dataobj.get_object_reference(cr, 1, 'base', 'group_partner_manager')
            result.append(group_id)
        except ValueError:
            # If these groups does not exists anymore
            pass
        return result

    _defaults = {
        'password' : '',
        'context_lang': 'en_US',
        'active' : True,
        'menu_id': _get_menu,
        'company_id': _get_company,
        'company_ids': _get_companies,
        'groups_id': _get_group,
        'address_id': False,
        'menu_tips':True
    }

    @tools.cache()
    def company_get(self, cr, uid, uid2, context=None):
        return self._get_company(cr, uid, context=context, uid2=uid2)

    # User can write to a few of her own fields (but not her groups for example)
    SELF_WRITEABLE_FIELDS = ['menu_tips','view', 'password', 'signature', 'action_id', 'company_id', 'user_email']

    def write(self, cr, uid, ids, values, context=None):
        if not hasattr(ids, '__iter__'):
            ids = [ids]
        if ids == [uid]:
            for key in values.keys():
                if not (key in self.SELF_WRITEABLE_FIELDS or key.startswith('context_')):
                    break
            else:
                if 'company_id' in values:
                    if not (values['company_id'] in self.read(cr, 1, uid, ['company_ids'], context=context)['company_ids']):
                        del values['company_id']
                uid = 1 # safe fields only, so we write as super-user to bypass access rights

        res = super(users, self).write(cr, uid, ids, values, context=context)

        # clear caches linked to the users
        self.company_get.clear_cache(cr.dbname)
        self.pool.get('ir.model.access').call_cache_clearing_methods(cr)
        clear = partial(self.pool.get('ir.rule').clear_cache, cr)
        map(clear, ids)
        db = cr.dbname
        if db in self._uid_cache:
            for id in ids:
                if id in self._uid_cache[db]:
                    del self._uid_cache[db][id]

        return res

    def unlink(self, cr, uid, ids, context=None):
        if 1 in ids:
            raise osv.except_osv(_('Can not remove root user!'), _('You can not remove the admin user as it is used internally for resources created by OpenERP (updates, module installation, ...)'))
        db = cr.dbname
        if db in self._uid_cache:
            for id in ids:
                if id in self._uid_cache[db]:
                    del self._uid_cache[db][id]
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

    def copy(self, cr, uid, id, default=None, context=None):
        user2copy = self.read(cr, uid, [id], ['login','name'])[0]
        if default is None:
            default = {}
        copy_pattern = _("%s (copy)")
        copydef = dict(login=(copy_pattern % user2copy['login']),
                       name=(copy_pattern % user2copy['name']),
                       address_id=False, # avoid sharing the address of the copied user!
                       )
        copydef.update(default)
        return super(users, self).copy(cr, uid, id, copydef, context)

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

    def action_get(self, cr, uid, context=None):
        dataobj = self.pool.get('ir.model.data')
        data_id = dataobj._get_id(cr, 1, 'base', 'action_res_users_my')
        return dataobj.browse(cr, uid, data_id, context=context).res_id


    def login(self, db, login, password):
        if not password:
            return False
        cr = pooler.get_db(db).cursor()
        try:
            cr.execute('UPDATE res_users SET date=now() WHERE login=%s AND password=%s AND active RETURNING id',
                    (tools.ustr(login), tools.ustr(password)))
            res = cr.fetchone()
            cr.commit()
            if res:
                return res[0]
            else:
                return False
        finally:
            cr.close()

    def check_super(self, passwd):
        if passwd == tools.config['admin_passwd']:
            return True
        else:
            raise security.ExceptionNoTb('AccessDenied')

    def check(self, db, uid, passwd):
        """Verifies that the given (uid, password) pair is authorized for the database ``db`` and
           raise an exception if it is not."""
        if not passwd:
            # empty passwords disallowed for obvious security reasons
            raise security.ExceptionNoTb('AccessDenied')
        if self._uid_cache.get(db, {}).get(uid) == passwd:
            return
        cr = pooler.get_db(db).cursor()
        try:
            cr.execute('SELECT COUNT(1) FROM res_users WHERE id=%s AND password=%s AND active=%s',
                        (int(uid), passwd, True))
            res = cr.fetchone()[0]
            if not res:
                raise security.ExceptionNoTb('AccessDenied')
            if self._uid_cache.has_key(db):
                ulist = self._uid_cache[db]
                ulist[uid] = passwd
            else:
                self._uid_cache[db] = {uid:passwd}
        finally:
            cr.close()

    def access(self, db, uid, passwd, sec_level, ids):
        if not passwd:
            return False
        cr = pooler.get_db(db).cursor()
        try:
            cr.execute('SELECT id FROM res_users WHERE id=%s AND password=%s', (uid, passwd))
            res = cr.fetchone()
            if not res:
                raise security.ExceptionNoTb('Bad username or password')
            return res[0]
        finally:
            cr.close()

    def change_password(self, cr, uid, old_passwd, new_passwd, context=None):
        """Change current user password. Old password must be provided explicitly
        to prevent hijacking an existing user session, or for cases where the cleartext
        password is not used to authenticate requests.

        :return: True
        :raise: security.ExceptionNoTb when old password is wrong
        :raise: except_osv when new password is not set or empty
        """
        self.check(cr.dbname, uid, old_passwd)
        if new_passwd:
            return self.write(cr, uid, uid, {'password': new_passwd})
        raise osv.except_osv(_('Warning!'), _("Setting empty passwords is not allowed for security reasons!"))

users()

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
        'view':lambda self,cr,uid,*args: self.pool.get('res.users').browse(cr, uid, uid).view or 'simple',
    }

    def execute(self, cr, uid, ids, context=None):
        res = self.read(cr, uid, ids)[0]
        self.pool.get('res.users').write(cr, uid, [uid],
                                 {'view':res['view']}, context=context)

res_config_view()



#
# Extension of res.groups and res.users with a relation for "implied" or 
# "inherited" groups.  Once a user belongs to a group, it automatically belongs
# to the implied groups (transitively).
#

class groups_implied(osv.osv):
    _inherit = 'res.groups'
    _columns = {
        'implied_ids': fields.many2many('res.groups', 'res_groups_implied_rel', 'gid', 'hid',
            string='Inherits', help='Users of this group automatically inherit those groups'),
    }

    def get_closure(self, cr, uid, ids, context=None):
        "return the closure of ids, i.e., all groups recursively implied by ids"
        closure = set()
        todo = self.browse(cr, 1, ids)
        while todo:
            g = todo.pop()
            if g.id not in closure:
                closure.add(g.id)
                todo.extend(g.implied_ids)
        return list(closure)

    def create(self, cr, uid, values, context=None):
        users = values.pop('users', None)
        gid = super(groups_implied, self).create(cr, uid, values, context)
        if users:
            # delegate addition of users to add implied groups
            self.write(cr, uid, [gid], {'users': users}, context)
        return gid

    def write(self, cr, uid, ids, values, context=None):
        res = super(groups_implied, self).write(cr, uid, ids, values, context)
        if values.get('users') or values.get('implied_ids'):
            # add implied groups (to all users of each group)
            for g in self.browse(cr, uid, ids):
                gids = self.get_closure(cr, uid, [g.id], context)
                users = [(4, u.id) for u in g.users]
                super(groups_implied, self).write(cr, uid, gids, {'users': users}, context)
        return res

    def get_maximal(self, cr, uid, ids, context=None):
        "return the maximal element among the group ids"
        max_set, max_closure = set(), set()
        for gid in ids:
            if gid not in max_closure:
                closure = set(self.get_closure(cr, uid, [gid], context))
                max_set -= closure          # remove implied groups from max_set
                max_set.add(gid)            # gid is maximal
                max_closure |= closure      # update closure of max_set
        if len(max_set) > 1:
            log = logging.getLogger('res.groups')
            log.warning('Groups %s are maximal among %s, only one expected.', max_set, ids)
        return bool(max_set) and max_set.pop()

groups_implied()

class users_implied(osv.osv):
    _inherit = 'res.users'

    def create(self, cr, uid, values, context=None):
        groups = values.pop('groups_id')
        user_id = super(users_implied, self).create(cr, uid, values, context)
        if groups:
            # delegate addition of groups to add implied groups
            self.write(cr, uid, [user_id], {'groups_id': groups}, context)
        return user_id

    def write(self, cr, uid, ids, values, context=None):
        res = super(users_implied, self).write(cr, uid, ids, values, context)
        if values.get('groups_id'):
            # add implied groups for all users
            groups_obj = self.pool.get('res.groups')
            for u in self.browse(cr, uid, ids):
                old_gids = map(int, u.groups_id)
                new_gids = groups_obj.get_closure(cr, uid, old_gids, context)
                if len(old_gids) != len(new_gids):
                    values = {'groups_id': [(6, 0, new_gids)]}
                    super(users_implied, self).write(cr, uid, [u.id], values, context)
        return res

users_implied()



#
# Extension of res.groups and res.users for the special groups view in the users
# form.  This extension presents groups with selection and boolean widgets:
# - Groups named as "App/Name" (corresponding to root menu "App") are presented
#   per application, with one boolean and selection field each.  The selection
#   field defines a role "Name" for the given application.
# - Groups named as "Stuff/Name" are presented as boolean fields and grouped
#   under sections "Stuff".
# - The remaining groups are presented as boolean fields and grouped in a
#   section "Others".
#

class groups_view(osv.osv):
    _inherit = 'res.groups'

    def get_classified(self, cr, uid, context=None):
        """ classify all groups by prefix; return a pair (apps, others) where
            - both are lists like [("App", [("Name", browse_group), ...]), ...];
            - apps is sorted in menu order;
            - others are sorted in alphabetic order;
            - groups not like App/Name are at the end of others, under _('Others')
        """
        # sort groups by implication, with implied groups first
        groups = self.browse(cr, uid, self.search(cr, uid, []), context)
        groups.sort(key=lambda g: set(self.get_closure(cr, uid, [g.id], context)))
        
        # classify groups depending on their names
        classified = {}
        for g in groups:
            # split() returns 1 or 2 elements, so names[-2] is prefix or None
            names = [None] + [s.strip() for s in g.name.split('/', 1)]
            classified.setdefault(names[-2], []).append((names[-1], g))
        
        # determine the apps (that correspond to root menus, in order)
        menu_obj = self.pool.get('ir.ui.menu')
        menu_ids = menu_obj.search(cr, uid, [('parent_id','=',False)], context={'ir.ui.menu.full_list': True})
        apps = []
        for m in menu_obj.browse(cr, uid, menu_ids, context):
            if m.name in classified:
                # application groups are already sorted by implication
                apps.append((m.name, classified.pop(m.name)))
        
        # other groups
        others = sorted(classified.items(), key=lambda pair: pair[0])
        if others and others[0][0] is None:
            others.append((_('Others'), others.pop(0)[1]))
        for sec, groups in others:
            groups.sort(key=lambda pair: pair[0])
        
        return (apps, others)

groups_view()

# Naming conventions for reified groups fields:
# - boolean field 'in_group_ID' is True iff
#       ID is in 'groups_id'
# - boolean field 'in_groups_ID1_..._IDk' is True iff
#       any of ID1, ..., IDk is in 'groups_id'
# - selection field 'sel_groups_ID1_..._IDk' is ID iff
#       ID is in 'groups_id' and ID is maximal in the set {ID1, ..., IDk}

def name_boolean_group(id): return 'in_group_' + str(id)
def name_boolean_groups(ids): return 'in_groups_' + '_'.join(map(str, ids))
def name_selection_groups(ids): return 'sel_groups_' + '_'.join(map(str, ids))

def is_boolean_group(name): return name.startswith('in_group_')
def is_boolean_groups(name): return name.startswith('in_groups_')
def is_selection_groups(name): return name.startswith('sel_groups_')
def is_field_group(name):
    return is_boolean_group(name) or is_boolean_groups(name) or is_selection_groups(name)

def get_boolean_group(name): return int(name[9:])
def get_boolean_groups(name): return map(int, name[10:].split('_'))
def get_selection_groups(name): return map(int, name[11:].split('_'))

def encode(s): return s.encode('utf8') if isinstance(s, unicode) else s
def partition(f, xs):
    "return a pair equivalent to (filter(f, xs), filter(lambda x: not f(x), xs))"
    yes, nos = [], []
    for x in xs:
        if f(x):
            yes.append(x)
        else:
            nos.append(x)
    return yes, nos

class users_view(osv.osv):
    _inherit = 'res.users'

    def _process_values_groups(self, cr, uid, values, context=None):
        """ transform all reified group fields into a 'groups_id', adding 
            also the implied groups """
        add, rem = [], []
        for k in values.keys():
            if is_boolean_group(k):
                if values.pop(k):
                    add.append(get_boolean_group(k))
                else:
                    rem.append(get_boolean_group(k))
            elif is_boolean_groups(k):
                if not values.pop(k):
                    rem.extend(get_boolean_groups(k))
            elif is_selection_groups(k):
                gid = values.pop(k)
                if gid:
                    rem.extend(get_selection_groups(k))
                    add.append(gid)
        if add or rem:
            # remove groups in 'rem' and add groups in 'add'
            gdiff = [(3, id) for id in rem] + [(4, id) for id in add]
            values.setdefault('groups_id', []).extend(gdiff)
        return True

    def create(self, cr, uid, values, context=None):
        self._process_values_groups(cr, uid, values, context)
        return super(users_view, self).create(cr, uid, values, context)

    def write(self, cr, uid, ids, values, context=None):
        self._process_values_groups(cr, uid, values, context)
        return super(users_view, self).write(cr, uid, ids, values, context)

    def read(self, cr, uid, ids, fields, context=None, load='_classic_read'):
        if not fields:
            group_fields, fields = [], self.fields_get(cr, uid, context).keys()
        else:
            group_fields, fields = partition(is_field_group, fields)
        if group_fields:
            group_obj = self.pool.get('res.groups')
            fields.append('groups_id')
            # read the normal fields (and 'groups_id')
            res = super(users_view, self).read(cr, uid, ids, fields, context, load)
            records = res if isinstance(res, list) else [res]
            for record in records:
                # get the field 'groups_id' and insert the group_fields
                groups = set(record['groups_id'])
                for f in group_fields:
                    if is_boolean_group(f):
                        record[f] = get_boolean_group(f) in groups
                    elif is_boolean_groups(f):
                        record[f] = not groups.isdisjoint(get_boolean_groups(f))
                    elif is_selection_groups(f):
                        selected = groups.intersection(get_selection_groups(f))
                        record[f] = group_obj.get_maximal(cr, uid, selected, context)
            return res
        return super(users_view, self).read(cr, uid, ids, fields, context, load)

    def fields_view_get(self, cr, uid, view_id=None, view_type='form',
                context=None, toolbar=False, submenu=False):
        # in form views, transform 'groups_id' into reified group fields
        res = super(users_view, self).fields_view_get(cr, uid, view_id, view_type,
                context, toolbar, submenu)
        if view_type == 'form':
            root = etree.fromstring(encode(res['arch']))
            nodes = root.xpath("//field[@name='groups_id']")
            if nodes:
                # replace node by the reified group fields
                fields = res['fields']
                elems = []
                apps, others = self.pool.get('res.groups').get_classified(cr, uid, context)
                # create section Applications
                elems.append('<separator colspan="6" string="%s"/>' % _('Applications'))
                for app, groups in apps:
                    ids = [g.id for name, g in groups]
                    app_name = name_boolean_groups(ids)
                    sel_name = name_selection_groups(ids)
                    selection = [(g.id, name) for name, g in groups]
                    fields[app_name] = {'type': 'boolean', 'string': app}
                    tips = [name + ': ' + (g.comment or '') for name, g in groups]
                    if tips:
                        fields[app_name].update(help='\n'.join(tips))
                    fields[sel_name] = {'type': 'selection', 'string': 'Group', 'selection': selection}
                    elems.append("""
                        <field name="%(app)s"/>
                        <field name="%(sel)s" nolabel="1" colspan="2"
                            attrs="{'invisible': [('%(app)s', '=', False)]}"
                            modifiers="{'invisible': [('%(app)s', '=', False)]}"/>
                        <newline/>
                        """ % {'app': app_name, 'sel': sel_name})
                # create other sections
                for sec, groups in others:
                    elems.append('<separator colspan="6" string="%s"/>' % sec)
                    for gname, g in groups:
                        name = name_boolean_group(g.id)
                        fields[name] = {'type': 'boolean', 'string': gname}
                        if g.comment:
                            fields[name].update(help=g.comment)
                        elems.append('<field name="%s"/>' % name)
                    elems.append('<newline/>')
                # replace xml node by new arch
                new_node = etree.fromstring('<group col="6">' + ''.join(elems) + '</group>')
                for node in nodes:
                    node.getparent().replace(node, new_node)
                res['arch'] = etree.tostring(root)
        return res

users_view()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
