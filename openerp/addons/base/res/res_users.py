# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#    Copyright (C) 2010-2014 OpenERP s.a. (<http://openerp.com>).
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
from functools import partial
import logging
from lxml import etree
from lxml.builder import E

import openerp
from openerp import SUPERUSER_ID
from openerp import tools
import openerp.exceptions
from openerp.osv import fields,osv, expression
from openerp.osv.orm import browse_record
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)

#----------------------------------------------------------
# Basic res.groups and res.users
#----------------------------------------------------------

class res_groups(osv.osv):
    _name = "res.groups"
    _description = "Access Groups"
    _rec_name = 'full_name'
    _order = 'name'

    def _get_full_name(self, cr, uid, ids, field, arg, context=None):
        res = {}
        for g in self.browse(cr, uid, ids, context):
            if g.category_id:
                res[g.id] = '%s / %s' % (g.category_id.name, g.name)
            else:
                res[g.id] = g.name
        return res

    def _search_group(self, cr, uid, obj, name, args, context=None):
        operand = args[0][2]
        operator = args[0][1]
        lst = True
        if isinstance(operand, bool):
            domains = [[('name', operator, operand)], [('category_id.name', operator, operand)]]
            if operator in expression.NEGATIVE_TERM_OPERATORS == (not operand):
                return expression.AND(domains)
            else:
                return expression.OR(domains)
        if isinstance(operand, basestring):
            lst = False
            operand = [operand]
        where = []
        for group in operand:
            values = filter(bool, group.split('/'))
            group_name = values.pop().strip()
            category_name = values and '/'.join(values).strip() or group_name
            group_domain = [('name', operator, lst and [group_name] or group_name)]
            category_domain = [('category_id.name', operator, lst and [category_name] or category_name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS and not values:
                category_domain = expression.OR([category_domain, [('category_id', '=', False)]])
            if (operator in expression.NEGATIVE_TERM_OPERATORS) == (not values):
                sub_where = expression.AND([group_domain, category_domain])
            else:
                sub_where = expression.OR([group_domain, category_domain])
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                where = expression.AND([where, sub_where])
            else:
                where = expression.OR([where, sub_where])
        return where

    _columns = {
        'name': fields.char('Name', size=64, required=True, translate=True),
        'users': fields.many2many('res.users', 'res_groups_users_rel', 'gid', 'uid', 'Users'),
        'model_access': fields.one2many('ir.model.access', 'group_id', 'Access Controls'),
        'rule_groups': fields.many2many('ir.rule', 'rule_group_rel',
            'group_id', 'rule_group_id', 'Rules', domain=[('global', '=', False)]),
        'menu_access': fields.many2many('ir.ui.menu', 'ir_ui_menu_group_rel', 'gid', 'menu_id', 'Access Menu'),
        'view_access': fields.many2many('ir.ui.view', 'ir_ui_view_group_rel', 'group_id', 'view_id', 'Views'),
        'comment' : fields.text('Comment', size=250, translate=True),
        'category_id': fields.many2one('ir.module.category', 'Application', select=True),
        'full_name': fields.function(_get_full_name, type='char', string='Group Name', fnct_search=_search_group),
    }

    _sql_constraints = [
        ('name_uniq', 'unique (category_id, name)', 'The name of the group must be unique within an application!')
    ]

    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        # add explicit ordering if search is sorted on full_name
        if order and order.startswith('full_name'):
            ids = super(res_groups, self).search(cr, uid, args, context=context)
            gs = self.browse(cr, uid, ids, context)
            gs.sort(key=lambda g: g.full_name, reverse=order.endswith('DESC'))
            gs = gs[offset:offset+limit] if limit else gs[offset:]
            return map(int, gs)
        return super(res_groups, self).search(cr, uid, args, offset, limit, order, context, count)

    def copy(self, cr, uid, id, default=None, context=None):
        group_name = self.read(cr, uid, [id], ['name'])[0]['name']
        default.update({'name': _('%s (copy)')%group_name})
        return super(res_groups, self).copy(cr, uid, id, default, context)

    def write(self, cr, uid, ids, vals, context=None):
        if 'name' in vals:
            if vals['name'].startswith('-'):
                raise osv.except_osv(_('Error'),
                        _('The name of the group can not start with "-"'))
        res = super(res_groups, self).write(cr, uid, ids, vals, context=context)
        self.pool['ir.model.access'].call_cache_clearing_methods(cr)
        return res

class res_users(osv.osv):
    """ User class. A res.users record models an OpenERP user and is different
        from an employee.

        res.users class now inherits from res.partner. The partner model is
        used to store the data related to the partner: lang, name, address,
        avatar, ... The user model is now dedicated to technical data.
    """
    __admin_ids = {}
    _uid_cache = {}
    _inherits = {
        'res.partner': 'partner_id',
    }
    _name = "res.users"
    _description = 'Users'

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
        'id': fields.integer('ID'),
        'login_date': fields.date('Latest connection', select=1),
        'partner_id': fields.many2one('res.partner', required=True,
            string='Related Partner', ondelete='restrict',
            help='Partner-related data of the user'),
        'login': fields.char('Login', size=64, required=True,
            help="Used to log into the system"),
        'password': fields.char('Password', size=64, invisible=True,
            help="Keep empty if you don't want the user to be able to connect on the system."),
        'new_password': fields.function(_get_password, type='char', size=64,
            fnct_inv=_set_new_password, string='Set Password',
            help="Specify a value only when creating a user or if you're "\
                 "changing the user's password, otherwise leave empty. After "\
                 "a change of password, the user has to login again."),
        'signature': fields.text('Signature'),
        'active': fields.boolean('Active'),
        'action_id': fields.many2one('ir.actions.actions', 'Home Action', help="If specified, this action will be opened at log on for this user, in addition to the standard menu."),
        'groups_id': fields.many2many('res.groups', 'res_groups_users_rel', 'uid', 'gid', 'Groups'),
        # Special behavior for this field: res.company.search() will only return the companies
        # available to the current user (should be the user's companies?), when the user_preference
        # context is set.
        'company_id': fields.many2one('res.company', 'Company', required=True,
            help='The company this user is currently working for.', context={'user_preference': True}),
        'company_ids':fields.many2many('res.company','res_company_users_rel','user_id','cid','Companies'),
    }

    def on_change_login(self, cr, uid, ids, login, context=None):
        if login and tools.single_email_re.match(login):
            return {'value': {'email': login}}
        return {}

    def onchange_state(self, cr, uid, ids, state_id, context=None):
        partner_ids = [user.partner_id.id for user in self.browse(cr, uid, ids, context=context)]
        return self.pool.get('res.partner').onchange_state(cr, uid, partner_ids, state_id, context=context)

    def onchange_type(self, cr, uid, ids, is_company, context=None):
        """ Wrapper on the user.partner onchange_type, because some calls to the
            partner form view applied to the user may trigger the
            partner.onchange_type method, but applied to the user object.
        """
        partner_ids = [user.partner_id.id for user in self.browse(cr, uid, ids, context=context)]
        return self.pool['res.partner'].onchange_type(cr, uid, partner_ids, is_company, context=context)

    def onchange_address(self, cr, uid, ids, use_parent_address, parent_id, context=None):
        """ Wrapper on the user.partner onchange_address, because some calls to the
            partner form view applied to the user may trigger the
            partner.onchange_type method, but applied to the user object.
        """
        partner_ids = [user.partner_id.id for user in self.browse(cr, uid, ids, context=context)]
        return self.pool['res.partner'].onchange_address(cr, uid, partner_ids, use_parent_address, parent_id, context=context)

    def _check_company(self, cr, uid, ids, context=None):
        return all(((this.company_id in this.company_ids) or not this.company_ids) for this in self.browse(cr, uid, ids, context))

    _constraints = [
        (_check_company, 'The chosen company is not in the allowed companies for this user', ['company_id', 'company_ids']),
    ]

    _sql_constraints = [
        ('login_key', 'UNIQUE (login)',  'You can not have two users with the same login !')
    ]

    def _get_company(self,cr, uid, context=None, uid2=False):
        if not uid2:
            uid2 = uid
        user = self.pool['res.users'].read(cr, uid, uid2, ['company_id'], context)
        company_id = user.get('company_id', False)
        return company_id and company_id[0] or False

    def _get_companies(self, cr, uid, context=None):
        c = self._get_company(cr, uid, context)
        if c:
            return [c]
        return False

    def _get_group(self,cr, uid, context=None):
        dataobj = self.pool.get('ir.model.data')
        result = []
        try:
            dummy,group_id = dataobj.get_object_reference(cr, SUPERUSER_ID, 'base', 'group_user')
            result.append(group_id)
            dummy,group_id = dataobj.get_object_reference(cr, SUPERUSER_ID, 'base', 'group_partner_manager')
            result.append(group_id)
        except ValueError:
            # If these groups does not exists anymore
            pass
        return result

    _defaults = {
        'password': '',
        'active': True,
        'customer': False,
        'company_id': _get_company,
        'company_ids': _get_companies,
        'groups_id': _get_group,
        'image': lambda self, cr, uid, ctx={}: self.pool['res.partner']._get_default_image(cr, uid, False, ctx, colorize=True),
    }

    # User can write on a few of his own fields (but not his groups for example)
    SELF_WRITEABLE_FIELDS = ['password', 'signature', 'action_id', 'company_id', 'email', 'name', 'image', 'image_medium', 'image_small', 'lang', 'tz']
    # User can read a few of his own fields
    SELF_READABLE_FIELDS = ['signature', 'company_id', 'login', 'email', 'name', 'image', 'image_medium', 'image_small', 'lang', 'tz', 'tz_offset', 'groups_id', 'partner_id', '__last_update']

    def read(self, cr, uid, ids, fields=None, context=None, load='_classic_read'):
        def override_password(o):
            if 'password' in o and ('id' not in o or o['id'] != uid):
                o['password'] = '********'
            return o

        if fields and (ids == [uid] or ids == uid):
            for key in fields:
                if not (key in self.SELF_READABLE_FIELDS or key.startswith('context_')):
                    break
            else:
                # safe fields only, so we read as super-user to bypass access rights
                uid = SUPERUSER_ID

        result = super(res_users, self).read(cr, uid, ids, fields=fields, context=context, load=load)
        canwrite = self.pool['ir.model.access'].check(cr, uid, 'res.users', 'write', False)
        if not canwrite:
            if isinstance(ids, (int, long)):
                result = override_password(result)
            else:
                result = map(override_password, result)

        return result

    def create(self, cr, uid, vals, context=None):
        user_id = super(res_users, self).create(cr, uid, vals, context=context)
        user = self.browse(cr, uid, user_id, context=context)
        if user.partner_id.company_id: 
            user.partner_id.write({'company_id': user.company_id.id})
        return user_id

    def write(self, cr, uid, ids, values, context=None):
        if not hasattr(ids, '__iter__'):
            ids = [ids]
        if ids == [uid]:
            for key in values.keys():
                if not (key in self.SELF_WRITEABLE_FIELDS or key.startswith('context_')):
                    break
            else:
                if 'company_id' in values:
                    if not (values['company_id'] in self.read(cr, SUPERUSER_ID, uid, ['company_ids'], context=context)['company_ids']):
                        del values['company_id']
                uid = 1 # safe fields only, so we write as super-user to bypass access rights

        res = super(res_users, self).write(cr, uid, ids, values, context=context)
        if 'company_id' in values:
            for user in self.browse(cr, uid, ids, context=context):
                # if partner is global we keep it that way
                if user.partner_id.company_id and user.partner_id.company_id.id != values['company_id']: 
                    user.partner_id.write({'company_id': user.company_id.id})
        # clear caches linked to the users
        self.pool['ir.model.access'].call_cache_clearing_methods(cr)
        clear = partial(self.pool['ir.rule'].clear_cache, cr)
        map(clear, ids)
        db = cr.dbname
        if db in self._uid_cache:
            for id in ids:
                if id in self._uid_cache[db]:
                    del self._uid_cache[db][id]
        self.context_get.clear_cache(self)
        return res

    def unlink(self, cr, uid, ids, context=None):
        if 1 in ids:
            raise osv.except_osv(_('Can not remove root user!'), _('You can not remove the admin user as it is used internally for resources created by OpenERP (updates, module installation, ...)'))
        db = cr.dbname
        if db in self._uid_cache:
            for id in ids:
                if id in self._uid_cache[db]:
                    del self._uid_cache[db][id]
        return super(res_users, self).unlink(cr, uid, ids, context=context)

    def name_search(self, cr, user, name='', args=None, operator='ilike', context=None, limit=100):
        if not args:
            args=[]
        if not context:
            context={}
        ids = []
        if name:
            ids = self.search(cr, user, [('login','=',name)]+ args, limit=limit, context=context)
        if not ids:
            ids = self.search(cr, user, [('name',operator,name)]+ args, limit=limit, context=context)
        return self.name_get(cr, user, ids, context=context)

    def copy(self, cr, uid, id, default=None, context=None):
        user2copy = self.read(cr, uid, [id], ['login','name'])[0]
        default = dict(default or {})
        if ('name' not in default) and ('partner_id' not in default):
            default['name'] = _("%s (copy)") % user2copy['name']
        if 'login' not in default:
            default['login'] = _("%s (copy)") % user2copy['login']
        return super(res_users, self).copy(cr, uid, id, default, context)

    @tools.ormcache(skiparg=2)
    def context_get(self, cr, uid, context=None):
        user = self.browse(cr, SUPERUSER_ID, uid, context)
        result = {}
        for k in self._all_columns.keys():
            if k.startswith('context_'):
                context_key = k[8:]
            elif k in ['lang', 'tz']:
                context_key = k
            else:
                context_key = False
            if context_key:
                res = getattr(user,k) or False
                if isinstance(res, browse_record):
                    res = res.id
                result[context_key] = res or False
        return result

    def action_get(self, cr, uid, context=None):
        dataobj = self.pool['ir.model.data']
        data_id = dataobj._get_id(cr, SUPERUSER_ID, 'base', 'action_res_users_my')
        return dataobj.browse(cr, uid, data_id, context=context).res_id

    def check_super(self, passwd):
        if passwd == tools.config['admin_passwd']:
            return True
        else:
            raise openerp.exceptions.AccessDenied()

    def check_credentials(self, cr, uid, password):
        """ Override this method to plug additional authentication methods"""
        res = self.search(cr, SUPERUSER_ID, [('id','=',uid),('password','=',password)])
        if not res:
            raise openerp.exceptions.AccessDenied()

    def login(self, db, login, password):
        if not password:
            return False
        user_id = False
        cr = self.pool.cursor()
        try:
            # autocommit: our single update request will be performed atomically.
            # (In this way, there is no opportunity to have two transactions
            # interleaving their cr.execute()..cr.commit() calls and have one
            # of them rolled back due to a concurrent access.)
            cr.autocommit(True)
            # check if user exists
            res = self.search(cr, SUPERUSER_ID, [('login','=',login)])
            if res:
                user_id = res[0]
                # check credentials
                self.check_credentials(cr, user_id, password)
                # We effectively unconditionally write the res_users line.
                # Even w/ autocommit there's a chance the user row will be locked,
                # in which case we can't delay the login just for the purpose of
                # update the last login date - hence we use FOR UPDATE NOWAIT to
                # try to get the lock - fail-fast
                # Failing to acquire the lock on the res_users row probably means
                # another request is holding it. No big deal, we don't want to
                # prevent/delay login in that case. It will also have been logged
                # as a SQL error, if anyone cares.
                try:
                    cr.execute("SELECT id FROM res_users WHERE id=%s FOR UPDATE NOWAIT", (user_id,), log_exceptions=False)
                    cr.execute("UPDATE res_users SET login_date = now() AT TIME ZONE 'UTC' WHERE id=%s", (user_id,))
                except Exception:
                    _logger.debug("Failed to update last_login for db:%s login:%s", db, login, exc_info=True)
        except openerp.exceptions.AccessDenied:
            _logger.info("Login failed for db:%s login:%s", db, login)
            user_id = False
        finally:
            cr.close()

        return user_id

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
                cr = self.pool.cursor()
                try:
                    base = user_agent_env['base_location']
                    ICP = self.pool['ir.config_parameter']
                    if not ICP.get_param(cr, uid, 'web.base.url.freeze'):
                        ICP.set_param(cr, uid, 'web.base.url', base)
                    cr.commit()
                except Exception:
                    _logger.exception("Failed to update web.base.url configuration parameter")
                finally:
                    cr.close()
        return uid

    def check(self, db, uid, passwd):
        """Verifies that the given (uid, password) is authorized for the database ``db`` and
           raise an exception if it is not."""
        if not passwd:
            # empty passwords disallowed for obvious security reasons
            raise openerp.exceptions.AccessDenied()
        if self._uid_cache.get(db, {}).get(uid) == passwd:
            return
        cr = self.pool.cursor()
        try:
            self.check_credentials(cr, uid, passwd)
            if self._uid_cache.has_key(db):
                self._uid_cache[db][uid] = passwd
            else:
                self._uid_cache[db] = {uid:passwd}
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

    def preference_save(self, cr, uid, ids, context=None):
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def preference_change_password(self, cr, uid, ids, context=None):
        return {
            'type': 'ir.actions.client',
            'tag': 'change_password',
            'target': 'new',
        }

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

#----------------------------------------------------------
# Implied groups
#
# Extension of res.groups and res.users with a relation for "implied"
# or "inherited" groups.  Once a user belongs to a group, it
# automatically belongs to the implied groups (transitively).
#----------------------------------------------------------

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
        for g in self.browse(cr, SUPERUSER_ID, ids, context):
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
            for g in self.browse(cr, uid, ids, context=context):
                gids = map(int, g.trans_implied_ids)
                vals = {'users': [(4, u.id) for u in g.users]}
                super(groups_implied, self).write(cr, uid, gids, vals, context)
        return res

class users_implied(osv.osv):
    _inherit = 'res.users'

    def create(self, cr, uid, values, context=None):
        groups = values.pop('groups_id', None)
        user_id = super(users_implied, self).create(cr, uid, values, context)
        if groups:
            # delegate addition of groups to add implied groups
            self.write(cr, uid, [user_id], {'groups_id': groups}, context)
            self.pool['ir.ui.view'].clear_cache()
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
            self.pool['ir.ui.view'].clear_cache()
        return res

#----------------------------------------------------------
# Vitrual checkbox and selection for res.user form view
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
#----------------------------------------------------------

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
        # we have to try-catch this, because at first init the view does not exist
        # but we are already creating some basic groups
        view = self.pool['ir.model.data'].xmlid_to_object(cr, SUPERUSER_ID, 'base.user_groups_view', context=context)
        if view and view.exists() and view._table_name == 'ir.ui.view':
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

        # add "default_groups_ref" inside the context to set default value for group_id with xml values
        if 'groups_id' in fields and isinstance(context.get("default_groups_ref"), list):
            groups = []
            ir_model_data = self.pool.get('ir.model.data')
            for group_xml_id in context["default_groups_ref"]:
                group_split = group_xml_id.split('.')
                if len(group_split) != 2:
                    raise osv.except_osv(_('Invalid context value'), _('Invalid context default_groups_ref value (model.name_id) : "%s"') % group_xml_id)
                try:
                    temp, group_id = ir_model_data.get_object_reference(cr, uid, group_split[0], group_split[1])
                except ValueError:
                    group_id = False
                groups += [group_id]
            values['groups_id'] = groups
        return values

    def read(self, cr, uid, ids, fields=None, context=None, load='_classic_read'):
        fields_get = fields if fields is not None else self.fields_get(cr, uid, context=context).keys()
        group_fields, _ = partition(is_reified_group, fields_get)

        inject_groups_id = group_fields and fields and 'groups_id' not in fields
        if inject_groups_id:
            fields.append('groups_id')
        res = super(users_view, self).read(cr, uid, ids, fields, context=context, load=load)

        if res and group_fields:
            for values in (res if isinstance(res, list) else [res]):
                self._get_reified_groups(group_fields, values)
                if inject_groups_id:
                    values.pop('groups_id', None)
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
        for app, kind, gs in self.pool['res.groups'].get_groups_by_application(cr, uid, context):
            if kind == 'selection':
                # selection group field
                tips = ['%s: %s' % (g.name, g.comment) for g in gs if g.comment]
                res[name_selection_groups(map(int, gs))] = {
                    'type': 'selection',
                    'string': app and app.name or _('Other'),
                    'selection': [(False, '')] + [(g.id, g.name) for g in gs],
                    'help': '\n'.join(tips),
                    'exportable': False,
                    'selectable': False,
                }
            else:
                # boolean group fields
                for g in gs:
                    res[name_boolean_group(g.id)] = {
                        'type': 'boolean',
                        'string': g.name,
                        'help': g.comment,
                        'exportable': False,
                        'selectable': False,
                    }
        return res

#----------------------------------------------------------
# change password wizard
#----------------------------------------------------------

class change_password_wizard(osv.TransientModel):
    """
        A wizard to manage the change of users' passwords
    """

    _name = "change.password.wizard"
    _description = "Change Password Wizard"
    _columns = {
        'user_ids': fields.one2many('change.password.user', 'wizard_id', string='Users'),
    }

    def default_get(self, cr, uid, fields, context=None):
        if context == None:
            context = {}
        user_ids = context.get('active_ids', [])
        wiz_id = context.get('active_id', None)
        res = []
        users = self.pool.get('res.users').browse(cr, uid, user_ids, context=context)
        for user in users:
            res.append((0, 0, {
                'wizard_id': wiz_id,
                'user_id': user.id,
                'user_login': user.login,
            }))
        return {'user_ids': res}

    def change_password_button(self, cr, uid, id, context=None):
        wizard = self.browse(cr, uid, id, context=context)[0]
        need_reload = any(uid == user.user_id.id for user in wizard.user_ids)
        line_ids = [user.id for user in wizard.user_ids]

        self.pool.get('change.password.user').change_password_button(cr, uid, line_ids, context=context)
        # don't keep temporary password copies in the database longer than necessary
        self.pool.get('change.password.user').write(cr, uid, line_ids, {'new_passwd': False}, context=context)

        if need_reload:
            return {
                'type': 'ir.actions.client',
                'tag': 'reload'
            }

        return {'type': 'ir.actions.act_window_close'}

class change_password_user(osv.TransientModel):
    """
        A model to configure users in the change password wizard
    """

    _name = 'change.password.user'
    _description = 'Change Password Wizard User'
    _columns = {
        'wizard_id': fields.many2one('change.password.wizard', string='Wizard', required=True),
        'user_id': fields.many2one('res.users', string='User', required=True),
        'user_login': fields.char('User Login', readonly=True),
        'new_passwd': fields.char('New Password'),
    }
    _defaults = {
        'new_passwd': '',
    }

    def change_password_button(self, cr, uid, ids, context=None):
        for user in self.browse(cr, uid, ids, context=context):
            self.pool.get('res.users').write(cr, uid, user.user_id.id, {'password': user.new_passwd})


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
