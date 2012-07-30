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

import logging
from functools import partial

import pytz

from lxml import etree
from lxml.builder import E
import netsvc
import openerp
import openerp.exceptions
from osv import fields,osv
from osv.orm import browse_record
import pooler
import random
from service import security
import tools
from tools.translate import _

_logger = logging.getLogger(__name__)

class groups(osv.osv):
    _name = "res.groups"
    _description = "Access Groups"
    _rec_name = 'full_name'

    def _get_full_name(self, cr, uid, ids, field, arg, context=None):
        res = {}
        for g in self.browse(cr, uid, ids, context):
            if g.category_id:
                res[g.id] = '%s / %s' % (g.category_id.name, g.name)
            else:
                res[g.id] = g.name
        return res

    _columns = {
        'name': fields.char('Name', size=64, required=True, translate=True),
        'users': fields.many2many('res.users', 'res_groups_users_rel', 'gid', 'uid', 'Users'),
        'model_access': fields.one2many('ir.model.access', 'group_id', 'Access Controls'),
        'rule_groups': fields.many2many('ir.rule', 'rule_group_rel',
            'group_id', 'rule_group_id', 'Rules', domain=[('global', '=', False)]),
        'menu_access': fields.many2many('ir.ui.menu', 'ir_ui_menu_group_rel', 'gid', 'menu_id', 'Access Menu'),
        'comment' : fields.text('Comment', size=250, translate=True),
        'category_id': fields.many2one('ir.module.category', 'Application', select=True),
        'full_name': fields.function(_get_full_name, type='char', string='Group Name'),
    }

    _sql_constraints = [
        ('name_uniq', 'unique (category_id, name)', 'The name of the group must be unique !')
    ]

    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        # add explicit ordering if search is sorted on full_name
        if order and order.startswith('full_name'):
            ids = super(groups, self).search(cr, uid, args, context=context)
            gs = self.browse(cr, uid, ids, context)
            gs.sort(key=lambda g: g.full_name, reverse=order.endswith('DESC'))
            gs = gs[offset:offset+limit] if limit else gs[offset:]
            return map(int, gs)
        return super(groups, self).search(cr, uid, args, offset, limit, order, context, count)

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
    _description = 'Users'
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
        if isinstance(id,list): id = id[0]
        user = self.read(cr, uid, id, ['email','login','name', 'user_email'], context=context)
        email = user['email'] or user['user_email']

        ir_mail_server = self.pool.get('ir.mail_server')
        msg = ir_mail_server.build_email(email_from=None, # take config default
                                         email_to=[email],
                                         subject=self.get_welcome_mail_subject(cr, uid, context=context),
                                         body=(self.get_welcome_mail_body(cr, uid, context=context) % user))
        return ir_mail_server.send_email(cr, uid, msg, context=context)

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

    def _get_image(self, cr, uid, ids, name, args, context=None):
        result = dict.fromkeys(ids, False)
        for obj in self.browse(cr, uid, ids, context=context):
            resized_image_dict = tools.get_resized_images(obj.image)
            result[obj.id] = {
                'image_medium': resized_image_dict['image_medium'],
                'image_small': resized_image_dict['image_small'],
                }
        return result
    
    def _set_image(self, cr, uid, id, name, value, args, context=None):
        return self.write(cr, uid, [id], {'image': tools.resize_image_big(value)}, context=context)
    
    def onchange_image(self, cr, uid, ids, value, context=None):
        return {'value': tools.get_resized_images(value)}
    
    _columns = {
        'id': fields.integer('ID'),
        'name': fields.char('User Name', size=64, required=True, select=True,
                            help="The new user's real name, used for searching"
                                 " and most listings"),
        'login': fields.char('Login', size=64, required=True,
                             help="Used to log into the system"),
        'password': fields.char('Password', size=64, invisible=True, help="Keep empty if you don't want the user to be able to connect on the system."),
        'new_password': fields.function(_get_password, type='char', size=64,
                                fnct_inv=_set_new_password,
                                string='Set Password', help="Specify a value only when creating a user or if you're changing the user's password, "
                                                            "otherwise leave empty. After a change of password, the user has to login again."),
        'user_email': fields.char('Email', size=64),
        'signature': fields.text('Signature', size=64),
        'image': fields.binary("Avatar",
            help="This field holds the image used as avatar for the "\
                 "user. The image is base64 encoded, and PIL-supported. "\
                 "It is limited to a 12024x1024 px image."),
        'image_medium': fields.function(_get_image, fnct_inv=_set_image,
            string="Medium-sized avatar", type="binary", multi="_get_image",
            store = {
                'res.users': (lambda self, cr, uid, ids, c={}: ids, ['image'], 10),
            },
            help="Medium-sized image of the user. It is automatically "\
                 "resized as a 180x180px image, with aspect ratio kept. "\
                 "Use this field in form views or some kanban views."),
        'image_small': fields.function(_get_image, fnct_inv=_set_image,
            string="Smal-sized avatar", type="binary", multi="_get_image",
            store = {
                'res.users': (lambda self, cr, uid, ids, c={}: ids, ['image'], 10),
            },
            help="Small-sized image of the user. It is automatically "\
                 "resized as a 50x50px image, with aspect ratio keps. "\
                 "Use this field anywhere a small image is required."),
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
            help="The default language used in the graphical user interface, when translations are available. To add a new language, you can use the 'Load a Translation' wizard available from the 'Administration' menu."),
        'context_tz': fields.selection(_tz_get,  'Timezone', size=64,
            help="The user's timezone, used to output proper date and time values inside printed reports. "
                 "It is important to set a value for this field. You should use the same timezone "
                 "that is otherwise used to pick and render date and time values: your computer's timezone."),
        'date': fields.datetime('Latest Connection', readonly=True),
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
        canwrite = self.pool.get('ir.model.access').check(cr, uid, 'res.users', 'write', False)
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

    def _get_default_image(self, cr, uid, context=None):
        # default image file name: avatar0 -> avatar6.png, choose randomly
        image_path = openerp.modules.get_module_resource('base', 'static/src/img', 'avatar%d.png' % random.randint(0, 6))
        return tools.resize_image_big(open(image_path, 'rb').read().encode('base64'))

    _defaults = {
        'password' : '',
        'context_lang': lambda self, cr, uid, context: context.get('lang', 'en_US'),
        'context_tz': lambda self, cr, uid, context: context.get('tz', False),
        'image': _get_default_image,
        'active' : True,
        'menu_id': _get_menu,
        'company_id': _get_company,
        'company_ids': _get_companies,
        'groups_id': _get_group,
    }

    # User can write to a few of her own fields (but not her groups for example)
    SELF_WRITEABLE_FIELDS = ['password', 'signature', 'action_id', 'company_id', 'user_email', 'name', 'image', 'image_medium', 'image_small']

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

    def authenticate(self, db, login, password, user_agent_env):
        """Verifies and returns the user ID corresponding to the given
          ``login`` and ``password`` combination, or False if there was
          no matching user.

           :param str db: the database on which user is trying to authenticate
           :param str login: username
           :param str password: user password
           :param dict user_agent_env: environment dictionary describing any
               relevant environment attributes
        """
        uid = self.login(db, login, password)
        if uid == openerp.SUPERUSER_ID:
            # Successfully logged in as admin!
            # Attempt to guess the web base url...
            if user_agent_env and user_agent_env.get('base_location'):
                cr = pooler.get_db(db).cursor()
                try:
                    self.pool.get('ir.config_parameter').set_param(cr, uid, 'web.base.url',
                                                                   user_agent_env['base_location'])
                    cr.commit()
                except Exception:
                    _logger.exception("Failed to update web.base.url configuration parameter")
                finally:
                    cr.close()
        return uid

    def login(self, db, login, password):
        if not password:
            return False
        cr = pooler.get_db(db).cursor()
        try:
            # autocommit: our single request will be performed atomically.
            # (In this way, there is no opportunity to have two transactions
            # interleaving their cr.execute()..cr.commit() calls and have one
            # of them rolled back due to a concurrent access.)
            # We effectively unconditionally write the res_users line.
            cr.autocommit(True)
            # Even w/ autocommit there's a chance the user row will be locked,
            # in which case we can't delay the login just for the purpose of
            # update the last login date - hence we use FOR UPDATE NOWAIT to
            # try to get the lock - fail-fast
            cr.execute("""SELECT id from res_users
                          WHERE login=%s AND password=%s
                                AND active FOR UPDATE NOWAIT""",
                       (tools.ustr(login), tools.ustr(password)))
            cr.execute("""UPDATE res_users
                            SET date = now() AT TIME ZONE 'UTC'
                            WHERE login=%s AND password=%s AND active
                            RETURNING id""",
                       (tools.ustr(login), tools.ustr(password)))
        except Exception:
            # Failing to acquire the lock on the res_users row probably means
            # another request is holding it. No big deal, we don't want to
            # prevent/delay login in that case. It will also have been logged
            # as a SQL error, if anyone cares.
            cr.execute("""SELECT id from res_users
                          WHERE login=%s AND password=%s
                                AND active""",
                       (tools.ustr(login), tools.ustr(password)))
        finally:
            res = cr.fetchone()
            cr.close()
            if res:
                return res[0]
        return False

    def check_super(self, passwd):
        if passwd == tools.config['admin_passwd']:
            return True
        else:
            raise openerp.exceptions.AccessDenied()

    def check(self, db, uid, passwd):
        """Verifies that the given (uid, password) pair is authorized for the database ``db`` and
           raise an exception if it is not."""
        if not passwd:
            # empty passwords disallowed for obvious security reasons
            raise openerp.exceptions.AccessDenied()
        if self._uid_cache.get(db, {}).get(uid) == passwd:
            return
        cr = pooler.get_db(db).cursor()
        try:
            cr.execute('SELECT COUNT(1) FROM res_users WHERE id=%s AND password=%s AND active=%s',
                        (int(uid), passwd, True))
            res = cr.fetchone()[0]
            if not res:
                raise openerp.exceptions.AccessDenied()
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
                raise openerp.exceptions.AccessDenied()
            return res[0]
        finally:
            cr.close()

    def change_password(self, cr, uid, old_passwd, new_passwd, context=None):
        """Change current user password. Old password must be provided explicitly
        to prevent hijacking an existing user session, or for cases where the cleartext
        password is not used to authenticate requests.

        :return: True
        :raise: openerp.exceptions.AccessDenied when old password is wrong
        :raise: except_osv when new password is not set or empty
        """
        self.check(cr.dbname, uid, old_passwd)
        if new_passwd:
            return self.write(cr, uid, uid, {'password': new_passwd})
        raise osv.except_osv(_('Warning!'), _("Setting empty passwords is not allowed for security reasons!"))

    def has_group(self, cr, uid, group_ext_id):
        """Checks whether user belongs to given group.

        :param str group_ext_id: external ID (XML ID) of the group.
           Must be provided in fully-qualified form (``module.ext_id``), as there
           is no implicit module to use..
        :return: True if the current user is a member of the group with the
           given external ID (XML ID), else False.
        """
        assert group_ext_id and '.' in group_ext_id, "External ID must be fully qualified"
        module, ext_id = group_ext_id.split('.')
        cr.execute("""SELECT 1 FROM res_groups_users_rel WHERE uid=%s AND gid IN 
                        (SELECT res_id FROM ir_model_data WHERE module=%s AND name=%s)""",
                   (uid, module, ext_id))
        return bool(cr.fetchone())

users()



#
# Extension of res.groups and res.users with a relation for "implied" or 
# "inherited" groups.  Once a user belongs to a group, it automatically belongs
# to the implied groups (transitively).
#

class cset(object):
    """ A cset (constrained set) is a set of elements that may be constrained to
        be a subset of other csets.  Elements added to a cset are automatically
        added to its supersets.  Cycles in the subset constraints are supported.
    """
    def __init__(self, xs):
        self.supersets = set()
        self.elements = set(xs)
    def subsetof(self, other):
        if other is not self:
            self.supersets.add(other)
            other.update(self.elements)
    def update(self, xs):
        xs = set(xs) - self.elements
        if xs:      # xs will eventually be empty in case of a cycle
            self.elements.update(xs)
            for s in self.supersets:
                s.update(xs)
    def __iter__(self):
        return iter(self.elements)

def concat(ls):
    """ return the concatenation of a list of iterables """
    res = []
    for l in ls: res.extend(l)
    return res



class groups_implied(osv.osv):
    _inherit = 'res.groups'

    def _get_trans_implied(self, cr, uid, ids, field, arg, context=None):
        "computes the transitive closure of relation implied_ids"
        memo = {}           # use a memo for performance and cycle avoidance
        def computed_set(g):
            if g not in memo:
                memo[g] = cset(g.implied_ids)
                for h in g.implied_ids:
                    computed_set(h).subsetof(memo[g])
            return memo[g]

        res = {}
        for g in self.browse(cr, 1, ids, context):
            res[g.id] = map(int, computed_set(g))
        return res

    _columns = {
        'implied_ids': fields.many2many('res.groups', 'res_groups_implied_rel', 'gid', 'hid',
            string='Inherits', help='Users of this group automatically inherit those groups'),
        'trans_implied_ids': fields.function(_get_trans_implied,
            type='many2many', relation='res.groups', string='Transitively inherits'),
    }

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
            # add all implied groups (to all users of each group)
            for g in self.browse(cr, uid, ids):
                gids = map(int, g.trans_implied_ids)
                vals = {'users': [(4, u.id) for u in g.users]}
                super(groups_implied, self).write(cr, uid, gids, vals, context)
        return res

groups_implied()

class users_implied(osv.osv):
    _inherit = 'res.users'

    def create(self, cr, uid, values, context=None):
        groups = values.pop('groups_id', None)
        user_id = super(users_implied, self).create(cr, uid, values, context)
        if groups:
            # delegate addition of groups to add implied groups
            self.write(cr, uid, [user_id], {'groups_id': groups}, context)
        return user_id

    def write(self, cr, uid, ids, values, context=None):
        if not isinstance(ids,list):
            ids = [ids]
        res = super(users_implied, self).write(cr, uid, ids, values, context)
        if values.get('groups_id'):
            # add implied groups for all users
            for user in self.browse(cr, uid, ids):
                gs = set(concat([g.trans_implied_ids for g in user.groups_id]))
                vals = {'groups_id': [(4, g.id) for g in gs]}
                super(users_implied, self).write(cr, uid, [user.id], vals, context)
        return res

users_implied()



#
# Extension of res.groups and res.users for the special groups view in the users
# form.  This extension presents groups with selection and boolean widgets:
# - Groups are shown by application, with boolean and/or selection fields.
#   Selection fields typically defines a role "Name" for the given application.
# - Uncategorized groups are presented as boolean fields and grouped in a
#   section "Others".
#
# The user form view is modified by an inherited view (base.user_groups_view);
# the inherited view replaces the field 'groups_id' by a set of reified group
# fields (boolean or selection fields).  The arch of that view is regenerated
# each time groups are changed.
#
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
def is_reified_group(name):
    return is_boolean_group(name) or is_boolean_groups(name) or is_selection_groups(name)

def get_boolean_group(name): return int(name[9:])
def get_boolean_groups(name): return map(int, name[10:].split('_'))
def get_selection_groups(name): return map(int, name[11:].split('_'))

def partition(f, xs):
    "return a pair equivalent to (filter(f, xs), filter(lambda x: not f(x), xs))"
    yes, nos = [], []
    for x in xs:
        (yes if f(x) else nos).append(x)
    return yes, nos



class groups_view(osv.osv):
    _inherit = 'res.groups'

    def create(self, cr, uid, values, context=None):
        res = super(groups_view, self).create(cr, uid, values, context)
        self.update_user_groups_view(cr, uid, context)
        return res

    def write(self, cr, uid, ids, values, context=None):
        res = super(groups_view, self).write(cr, uid, ids, values, context)
        self.update_user_groups_view(cr, uid, context)
        return res

    def unlink(self, cr, uid, ids, context=None):
        res = super(groups_view, self).unlink(cr, uid, ids, context)
        self.update_user_groups_view(cr, uid, context)
        return res

    def update_user_groups_view(self, cr, uid, context=None):
        # the view with id 'base.user_groups_view' inherits the user form view,
        # and introduces the reified group fields
        view = self.get_user_groups_view(cr, uid, context)
        if view:
            xml1, xml2 = [], []
            xml1.append(E.separator(string=_('Application'), colspan="4"))
            for app, kind, gs in self.get_groups_by_application(cr, uid, context):
                # hide groups in category 'Hidden' (except to group_no_one)
                attrs = {'groups': 'base.group_no_one'} if app and app.xml_id == 'base.module_category_hidden' else {}
                if kind == 'selection':
                    # application name with a selection field
                    field_name = name_selection_groups(map(int, gs))
                    xml1.append(E.field(name=field_name, **attrs))
                    xml1.append(E.newline())
                else:
                    # application separator with boolean fields
                    app_name = app and app.name or _('Other')
                    xml2.append(E.separator(string=app_name, colspan="4", **attrs))
                    for g in gs:
                        field_name = name_boolean_group(g.id)
                        xml2.append(E.field(name=field_name, **attrs))

            xml = E.field(*(xml1 + xml2), name="groups_id", position="replace")
            xml.addprevious(etree.Comment("GENERATED AUTOMATICALLY BY GROUPS"))
            xml_content = etree.tostring(xml, pretty_print=True, xml_declaration=True, encoding="utf-8")
            view.write({'arch': xml_content})
        return True

    def get_user_groups_view(self, cr, uid, context=None):
        try:
            view = self.pool.get('ir.model.data').get_object(cr, 1, 'base', 'user_groups_view', context)
            assert view and view._table_name == 'ir.ui.view'
        except Exception:
            view = False
        return view

    def get_application_groups(self, cr, uid, domain=None, context=None):
        return self.search(cr, uid, domain or [])

    def get_groups_by_application(self, cr, uid, context=None):
        """ return all groups classified by application (module category), as a list of pairs:
                [(app, kind, [group, ...]), ...],
            where app and group are browse records, and kind is either 'boolean' or 'selection'.
            Applications are given in sequence order.  If kind is 'selection', the groups are
            given in reverse implication order.
        """
        def linearized(gs):
            gs = set(gs)
            # determine sequence order: a group should appear after its implied groups
            order = dict.fromkeys(gs, 0)
            for g in gs:
                for h in gs.intersection(g.trans_implied_ids):
                    order[h] -= 1
            # check whether order is total, i.e., sequence orders are distinct
            if len(set(order.itervalues())) == len(gs):
                return sorted(gs, key=lambda g: order[g])
            return None

        # classify all groups by application
        gids = self.get_application_groups(cr, uid, context=context)
        by_app, others = {}, []
        for g in self.browse(cr, uid, gids, context):
            if g.category_id:
                by_app.setdefault(g.category_id, []).append(g)
            else:
                others.append(g)
        # build the result
        res = []
        apps = sorted(by_app.iterkeys(), key=lambda a: a.sequence or 0)
        for app in apps:
            gs = linearized(by_app[app])
            if gs:
                res.append((app, 'selection', gs))
            else:
                res.append((app, 'boolean', by_app[app]))
        if others:
            res.append((False, 'boolean', others))
        return res

groups_view()

class users_view(osv.osv):
    _inherit = 'res.users'

    def create(self, cr, uid, values, context=None):
        self._set_reified_groups(values)
        return super(users_view, self).create(cr, uid, values, context)

    def write(self, cr, uid, ids, values, context=None):
        self._set_reified_groups(values)
        return super(users_view, self).write(cr, uid, ids, values, context)

    def _set_reified_groups(self, values):
        """ reflect reified group fields in values['groups_id'] """
        if 'groups_id' in values:
            # groups are already given, ignore group fields
            for f in filter(is_reified_group, values.iterkeys()):
                del values[f]
            return

        add, remove = [], []
        for f in values.keys():
            if is_boolean_group(f):
                target = add if values.pop(f) else remove
                target.append(get_boolean_group(f))
            elif is_boolean_groups(f):
                if not values.pop(f):
                    remove.extend(get_boolean_groups(f))
            elif is_selection_groups(f):
                remove.extend(get_selection_groups(f))
                selected = values.pop(f)
                if selected:
                    add.append(selected)
        # update values *only* if groups are being modified, otherwise
        # we introduce spurious changes that might break the super.write() call.
        if add or remove:
            # remove groups in 'remove' and add groups in 'add'
            values['groups_id'] = [(3, id) for id in remove] + [(4, id) for id in add]

    def default_get(self, cr, uid, fields, context=None):
        group_fields, fields = partition(is_reified_group, fields)
        fields1 = (fields + ['groups_id']) if group_fields else fields
        values = super(users_view, self).default_get(cr, uid, fields1, context)
        self._get_reified_groups(group_fields, values)
        return values

    def read(self, cr, uid, ids, fields=None, context=None, load='_classic_read'):
        if not fields:
            fields = self.fields_get(cr, uid, context=context).keys()
        group_fields, fields = partition(is_reified_group, fields)
        if not 'groups_id' in fields:
            fields.append('groups_id')
        res = super(users_view, self).read(cr, uid, ids, fields, context=context, load=load)
        for values in (res if isinstance(res, list) else [res]):
            self._get_reified_groups(group_fields, values)
        return res

    def _get_reified_groups(self, fields, values):
        """ compute the given reified group fields from values['groups_id'] """
        gids = set(values.get('groups_id') or [])
        for f in fields:
            if is_boolean_group(f):
                values[f] = get_boolean_group(f) in gids
            elif is_boolean_groups(f):
                values[f] = not gids.isdisjoint(get_boolean_groups(f))
            elif is_selection_groups(f):
                selected = [gid for gid in get_selection_groups(f) if gid in gids]
                values[f] = selected and selected[-1] or False

    def fields_get(self, cr, uid, allfields=None, context=None, write_access=True):
        res = super(users_view, self).fields_get(cr, uid, allfields, context, write_access)
        # add reified groups fields
        for app, kind, gs in self.pool.get('res.groups').get_groups_by_application(cr, uid, context):
            if kind == 'selection':
                # selection group field
                tips = ['%s: %s' % (g.name, g.comment or '') for g in gs]
                res[name_selection_groups(map(int, gs))] = {
                    'type': 'selection',
                    'string': app and app.name or _('Other'),
                    'selection': [(False, '')] + [(g.id, g.name) for g in gs],
                    'help': '\n'.join(tips),
                }
            else:
                # boolean group fields
                for g in gs:
                    res[name_boolean_group(g.id)] = {
                        'type': 'boolean',
                        'string': g.name,
                        'help': g.comment,
                    }
        return res

users_view()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
