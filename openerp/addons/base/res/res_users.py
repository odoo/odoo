# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import itertools
import logging
from functools import partial
from itertools import repeat

from lxml import etree
from lxml.builder import E

import openerp
from openerp import api
from openerp import SUPERUSER_ID, models
from openerp import tools
import openerp.exceptions
from openerp import api
from openerp.osv import fields, osv, expression
from openerp.service.db import check_super
from openerp.tools.translate import _
from openerp.http import request
from openerp.exceptions import UserError

_logger = logging.getLogger(__name__)

# Only users who can modify the user (incl. the user herself) see the real contents of these fields
USER_PRIVATE_FIELDS = ['password']

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
        for g in self.browse(cr, SUPERUSER_ID, ids, context=context):
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
        'name': fields.char('Name', required=True, translate=True),
        'users': fields.many2many('res.users', 'res_groups_users_rel', 'gid', 'uid', 'Users'),
        'model_access': fields.one2many('ir.model.access', 'group_id', 'Access Controls', copy=True),
        'rule_groups': fields.many2many('ir.rule', 'rule_group_rel',
            'group_id', 'rule_group_id', 'Rules', domain=[('global', '=', False)]),
        'menu_access': fields.many2many('ir.ui.menu', 'ir_ui_menu_group_rel', 'gid', 'menu_id', 'Access Menu'),
        'view_access': fields.many2many('ir.ui.view', 'ir_ui_view_group_rel', 'group_id', 'view_id', 'Views'),
        'comment' : fields.text('Comment', size=250, translate=True),
        'category_id': fields.many2one('ir.module.category', 'Application', select=True),
        'color': fields.integer('Color Index'),
        'full_name': fields.function(_get_full_name, type='char', string='Group Name', fnct_search=_search_group),
        'share': fields.boolean('Share Group',
                    help="Group created to set access rights for sharing data with some users.")
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
                raise UserError(_('The name of the group can not start with "-"'))
        res = super(res_groups, self).write(cr, uid, ids, vals, context=context)
        self.pool['ir.model.access'].call_cache_clearing_methods(cr)
        self.pool['res.users'].has_group.clear_cache(self.pool['res.users'])
        return res

class ResUsersLog(osv.Model):
    _name = 'res.users.log'
    _order = 'id desc'
    # Currenly only uses the magical fields: create_uid, create_date,
    # for recording logins. To be extended for other uses (chat presence, etc.)

class res_users(osv.osv):
    """ User class. A res.users record models an OpenERP user and is different
        from an employee.

        res.users class now inherits from res.partner. The partner model is
        used to store the data related to the partner: lang, name, address,
        avatar, ... The user model is now dedicated to technical data.
    """
    __uid_cache = {}
    _inherits = {
        'res.partner': 'partner_id',
    }
    _name = "res.users"
    _description = 'Users'
    _order = 'name, login'

    def _set_new_password(self, cr, uid, id, name, value, args, context=None):
        if value is False:
            # Do not update the password if no value is provided, ignore silently.
            # For example web client submits False values for all empty fields.
            return
        if uid == id:
            # To change their own password users must use the client-specific change password wizard,
            # so that the new password is immediately used for further RPC requests, otherwise the user
            # will face unexpected 'Access Denied' exceptions.
            raise UserError(_('Please use the change password wizard (in User Preferences or User menu) to change your own password.'))
        self.write(cr, uid, id, {'password': value})

    def _get_password(self, cr, uid, ids, arg, karg, context=None):
        return dict.fromkeys(ids, '')

    def _is_share(self, cr, uid, ids, name, args, context=None):
        res = {}
        for user in self.browse(cr, uid, ids, context=context):
            res[user.id] = not self.has_group(cr, user.id, 'base.group_user')
        return res

    def _store_trigger_share_res_groups(self, cr, uid, ids, context=None):
        group_user = self.pool['ir.model.data'].xmlid_to_object(cr, SUPERUSER_ID, 'base.group_user', context=context)
        if group_user and group_user.id in ids:
            return group_user.users.ids
        return []

    def _get_users_from_group(self, cr, uid, ids, context=None):
        result = set()
        groups = self.pool['res.groups'].browse(cr, uid, ids, context=context)
        # Clear cache to avoid perf degradation on databases with thousands of users
        groups.invalidate_cache()
        for group in groups:
            result.update(user.id for user in group.users)
        return list(result)

    _columns = {
        'id': fields.integer('ID'),
        'partner_id': fields.many2one('res.partner', required=True,
            string='Related Partner', ondelete='restrict',
            help='Partner-related data of the user', auto_join=True),
        'login': fields.char('Login', size=64, required=True,
            help="Used to log into the system"),
        'password': fields.char('Password', size=64, invisible=True, copy=False,
            help="Keep empty if you don't want the user to be able to connect on the system."),
        'new_password': fields.function(_get_password, type='char', size=64,
            fnct_inv=_set_new_password, string='Set Password',
            help="Specify a value only when creating a user or if you're "\
                 "changing the user's password, otherwise leave empty. After "\
                 "a change of password, the user has to login again."),
        'signature': fields.html('Signature'),
        'active': fields.boolean('Active'),
        'action_id': fields.many2one('ir.actions.actions', 'Home Action', help="If specified, this action will be opened at log on for this user, in addition to the standard menu."),
        'groups_id': fields.many2many('res.groups', 'res_groups_users_rel', 'uid', 'gid', 'Groups'),
        # Special behavior for this field: res.company.search() will only return the companies
        # available to the current user (should be the user's companies?), when the user_preference
        # context is set.
        'company_id': fields.many2one('res.company', 'Company', required=True,
            help='The company this user is currently working for.', context={'user_preference': True}),
        'company_ids':fields.many2many('res.company','res_company_users_rel','user_id','cid','Companies'),
        'share': fields.function(_is_share, string='Share User', type='boolean',
             store={
                 'res.users': (lambda self, cr, uid, ids, c={}: ids, ['groups_id'], 50),
                 'res.groups': (_store_trigger_share_res_groups, ['users'], 50),
             }, help="External user with limited access, created only for the purpose of sharing data."),
    }

    # overridden inherited fields to bypass access rights, in case you have
    # access to the user but not its corresponding partner
    name = openerp.fields.Char(related='partner_id.name', inherited=True)
    email = openerp.fields.Char(related='partner_id.email', inherited=True)
    log_ids = openerp.fields.One2many('res.users.log', 'create_uid', string='User log entries')
    login_date = openerp.fields.Datetime(related='log_ids.create_date', string='Latest connection')

    def on_change_login(self, cr, uid, ids, login, context=None):
        if login and tools.single_email_re.match(login):
            return {'value': {'email': login}}
        return {}

    def onchange_state(self, cr, uid, ids, state_id, context=None):
        partner_ids = [user.partner_id.id for user in self.browse(cr, uid, ids, context=context)]
        return self.pool.get('res.partner').onchange_state(cr, uid, partner_ids, state_id, context=context)

    def onchange_parent_id(self, cr, uid, ids, parent_id, context=None):
        """ Wrapper on the user.partner onchange_address, because some calls to the
            partner form view applied to the user may trigger the
            partner.onchange_type method, but applied to the user object.
        """
        partner_ids = [user.partner_id.id for user in self.browse(cr, uid, ids, context=context)]
        return self.pool['res.partner'].onchange_address(cr, uid, partner_ids, parent_id, context=context)

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
        # Use read() to compute default company, and pass load=_classic_write to
        # avoid useless name_get() calls. This will avoid prefetching fields
        # while computing default values for new db columns, as the
        # db backend may not be fully initialized yet.
        user_data = self.pool['res.users'].read(cr, uid, uid2, ['company_id'],
                                                context=context, load='_classic_write')
        comp_id = user_data['company_id']
        return comp_id or False

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
    }

    # User can write on a few of his own fields (but not his groups for example)
    SELF_WRITEABLE_FIELDS = ['signature', 'action_id', 'company_id', 'email', 'name', 'image', 'image_medium', 'image_small', 'lang', 'tz']
    # User can read a few of his own fields
    SELF_READABLE_FIELDS = ['signature', 'company_id', 'login', 'email', 'name', 'image', 'image_medium', 'image_small', 'lang', 'tz', 'tz_offset', 'groups_id', 'partner_id', '__last_update', 'action_id']

    @api.multi
    def _read_from_database(self, field_names, inherited_field_names=[]):
        super(res_users, self)._read_from_database(field_names, inherited_field_names)
        canwrite = self.check_access_rights('write', raise_exception=False)
        if not canwrite and set(USER_PRIVATE_FIELDS).intersection(field_names):
            for record in self:
                for f in USER_PRIVATE_FIELDS:
                    try:
                        record._cache[f]
                        record._cache[f] = '********'
                    except Exception:
                        # skip SpecialValue (e.g. for missing record or access right)
                        pass

    def read(self, cr, uid, ids, fields=None, context=None, load='_classic_read'):
        if fields and (ids == [uid] or ids == uid):
            for key in fields:
                if not (key in self.SELF_READABLE_FIELDS or key.startswith('context_')):
                    break
            else:
                # safe fields only, so we read as super-user to bypass access rights
                uid = SUPERUSER_ID
        return super(res_users, self).read(cr, uid, ids, fields=fields, context=context, load=load)

    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False, lazy=True):
        if uid != SUPERUSER_ID:
            groupby_fields = set([groupby] if isinstance(groupby, basestring) else groupby)
            if groupby_fields.intersection(USER_PRIVATE_FIELDS):
                raise openerp.exceptions.AccessError('Invalid groupby')
        return super(res_users, self).read_group(
            cr, uid, domain, fields, groupby, offset=offset, limit=limit, context=context, orderby=orderby, lazy=lazy)

    def _search(self, cr, user, args, offset=0, limit=None, order=None, context=None, count=False, access_rights_uid=None):
        if user != SUPERUSER_ID and args:
            domain_terms = [term for term in args if isinstance(term, (tuple, list))]
            domain_fields = set(left for (left, op, right) in domain_terms)
            if domain_fields.intersection(USER_PRIVATE_FIELDS):
                raise openerp.exceptions.AccessError('Invalid search criterion')
        return super(res_users, self)._search(
            cr, user, args, offset=offset, limit=limit, order=order, context=context, count=count,
            access_rights_uid=access_rights_uid)

    def create(self, cr, uid, vals, context=None):
        user_id = super(res_users, self).create(cr, uid, vals, context=context)
        user = self.browse(cr, uid, user_id, context=context)
        user.partner_id.active = user.active
        if user.partner_id.company_id: 
            user.partner_id.write({'company_id': user.company_id.id})
        return user_id

    def write(self, cr, uid, ids, values, context=None):
        if not hasattr(ids, '__iter__'):
            ids = [ids]

        if values.get('active') == False:
            for current_id in ids:
                if current_id == SUPERUSER_ID:
                    raise UserError(_("You cannot unactivate the admin user."))
                elif current_id == uid:
                    raise UserError(_("You cannot unactivate the user you're currently logged in as."))

        if ids == [uid]:
            for key in values.keys():
                if not (key in self.SELF_WRITEABLE_FIELDS or key.startswith('context_')):
                    break
            else:
                if 'company_id' in values:
                    user = self.browse(cr, SUPERUSER_ID, uid, context=context)
                    if not (values['company_id'] in user.company_ids.ids):
                        del values['company_id']
                uid = 1 # safe fields only, so we write as super-user to bypass access rights

        res = super(res_users, self).write(cr, uid, ids, values, context=context)
        if 'company_id' in values:
            for user in self.browse(cr, uid, ids, context=context):
                # if partner is global we keep it that way
                if user.partner_id.company_id and user.partner_id.company_id.id != values['company_id']: 
                    user.partner_id.write({'company_id': user.company_id.id})
            # clear default ir values when company changes
            self.pool['ir.values'].get_defaults_dict.clear_cache(self.pool['ir.values'])
        # clear caches linked to the users
        self.pool['ir.model.access'].call_cache_clearing_methods(cr)
        clear = partial(self.pool['ir.rule'].clear_cache, cr)
        map(clear, ids)
        db = cr.dbname
        if db in self.__uid_cache:
            for id in ids:
                if id in self.__uid_cache[db]:
                    del self.__uid_cache[db][id]
        self.context_get.clear_cache(self)
        self.has_group.clear_cache(self)
        return res

    def unlink(self, cr, uid, ids, context=None):
        if 1 in ids:
            raise UserError(_('You can not remove the admin user as it is used internally for resources created by Odoo (updates, module installation, ...)'))
        db = cr.dbname
        if db in self.__uid_cache:
            for id in ids:
                if id in self.__uid_cache[db]:
                    del self.__uid_cache[db][id]
        return super(res_users, self).unlink(cr, uid, ids, context=context)

    def name_search(self, cr, user, name='', args=None, operator='ilike', context=None, limit=100):
        if not args:
            args=[]
        if not context:
            context={}
        ids = []
        if name and operator in ['=', 'ilike']:
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

    @tools.ormcache('uid')
    def context_get(self, cr, uid, context=None):
        user = self.browse(cr, SUPERUSER_ID, uid, context)
        result = {}
        for k in self._fields:
            if k.startswith('context_'):
                context_key = k[8:]
            elif k in ['lang', 'tz']:
                context_key = k
            else:
                context_key = False
            if context_key:
                res = getattr(user, k) or False
                if isinstance(res, models.BaseModel):
                    res = res.id
                result[context_key] = res or False
        return result

    def action_get(self, cr, uid, context=None):
        dataobj = self.pool['ir.model.data']
        data_id = dataobj._get_id(cr, SUPERUSER_ID, 'base', 'action_res_users_my')
        return dataobj.browse(cr, uid, data_id, context=context).res_id

    def check_super(self, passwd):
        return check_super(passwd)

    def check_credentials(self, cr, uid, password):
        """ Override this method to plug additional authentication methods"""
        res = self.search(cr, SUPERUSER_ID, [('id','=',uid),('password','=',password)])
        if not res:
            raise openerp.exceptions.AccessDenied()

    def _update_last_login(self, cr, uid):
        # only create new records to avoid any side-effect on concurrent transactions
        # extra records will be deleted by the periodical garbage collection
        self.pool['res.users.log'].create(cr, uid, {}) # populated by defaults

    def _login(self, db, login, password):
        if not password:
            return False
        user_id = False
        try:
            with self.pool.cursor() as cr:
                res = self.search(cr, SUPERUSER_ID, [('login','=',login)])
                if res:
                    user_id = res[0]
                    self.check_credentials(cr, user_id, password)
                    self._update_last_login(cr, user_id)
        except openerp.exceptions.AccessDenied:
            _logger.info("Login failed for db:%s login:%s", db, login)
            user_id = False
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
        uid = self._login(db, login, password)
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
        if self.__uid_cache.setdefault(db, {}).get(uid) == passwd:
            return
        cr = self.pool.cursor()
        try:
            self.check_credentials(cr, uid, passwd)
            self.__uid_cache[db][uid] = passwd
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
            return self.write(cr, SUPERUSER_ID, uid, {'password': new_passwd})
        raise UserError(_("Setting empty passwords is not allowed for security reasons!"))

    def preference_save(self, cr, uid, ids, context=None):
        return {
            'type': 'ir.actions.client',
            'tag': 'reload_context',
        }

    def preference_change_password(self, cr, uid, ids, context=None):
        return {
            'type': 'ir.actions.client',
            'tag': 'change_password',
            'target': 'new',
        }

    @api.v7
    def has_group(self, cr, uid, group_ext_id):
        return self._has_group(cr, uid, group_ext_id)
    @api.v8
    def has_group(self, group_ext_id):
        # use singleton's id if called on a non-empty recordset, otherwise
        # context uid
        uid = self.id or self.env.uid
        return self._has_group(self.env.cr, uid, group_ext_id)

    @api.noguess
    @tools.ormcache('uid', 'group_ext_id')
    def _has_group(self, cr, uid, group_ext_id):
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
    # for a few places explicitly clearing the has_group cache
    has_group.clear_cache = _has_group.clear_cache

    @api.multi
    def _is_admin(self):
        return self.id == openerp.SUPERUSER_ID or self.sudo(self).has_group('base.group_erp_manager')

    def get_company_currency_id(self, cr, uid, context=None):
        return self.browse(cr, uid, uid, context=context).company_id.currency_id.id

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

concat = itertools.chain.from_iterable

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
                gs = set(concat(g.trans_implied_ids for g in user.groups_id))
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
# - selection field 'sel_groups_ID1_..._IDk' is ID iff
#       ID is in 'groups_id' and ID is maximal in the set {ID1, ..., IDk}
#----------------------------------------------------------

def name_boolean_group(id):
    return 'in_group_' + str(id)

def name_selection_groups(ids):
    return 'sel_groups_' + '_'.join(map(str, ids))

def is_boolean_group(name):
    return name.startswith('in_group_')

def is_selection_groups(name):
    return name.startswith('sel_groups_')

def is_reified_group(name):
    return is_boolean_group(name) or is_selection_groups(name)

def get_boolean_group(name):
    return int(name[9:])

def get_selection_groups(name):
    return map(int, name[11:].split('_'))

def partition(f, xs):
    "return a pair equivalent to (filter(f, xs), filter(lambda x: not f(x), xs))"
    yes, nos = [], []
    for x in xs:
        (yes if f(x) else nos).append(x)
    return yes, nos

def parse_m2m(commands):
    "return a list of ids corresponding to a many2many value"
    ids = []
    for command in commands:
        if isinstance(command, (tuple, list)):
            if command[0] in (1, 4):
                ids.append(command[1])
            elif command[0] == 5:
                ids = []
            elif command[0] == 6:
                ids = list(command[2])
        else:
            ids.append(command)
    return ids


class groups_view(osv.osv):
    _inherit = 'res.groups'

    def create(self, cr, uid, values, context=None):
        res = super(groups_view, self).create(cr, uid, values, context)
        self.update_user_groups_view(cr, uid, context)
        # ir_values.get_actions() depends on action records
        self.pool['ir.values'].clear_caches()
        return res

    def write(self, cr, uid, ids, values, context=None):
        res = super(groups_view, self).write(cr, uid, ids, values, context)
        self.update_user_groups_view(cr, uid, context)
        # ir_values.get_actions() depends on action records
        self.pool['ir.values'].clear_caches()
        return res

    def unlink(self, cr, uid, ids, context=None):
        res = super(groups_view, self).unlink(cr, uid, ids, context)
        self.update_user_groups_view(cr, uid, context)
        # ir_values.get_actions() depends on action records
        self.pool['ir.values'].clear_caches()
        return res

    def update_user_groups_view(self, cr, uid, context=None):
        # the view with id 'base.user_groups_view' inherits the user form view,
        # and introduces the reified group fields
        # we have to try-catch this, because at first init the view does not exist
        # but we are already creating some basic groups
        user_context = dict(context or {})
        if user_context.get('install_mode'):
            # use installation/admin language for translatable names in the view
            user_context.update(self.pool['res.users'].context_get(cr, uid))
        view = self.pool['ir.model.data'].xmlid_to_object(cr, SUPERUSER_ID, 'base.user_groups_view', context=user_context)
        if view and view.exists() and view._name == 'ir.ui.view':
            group_no_one = view.env.ref('base.group_no_one')
            xml1, xml2 = [], []
            xml1.append(E.separator(string=_('Application'), colspan="2"))
            for app, kind, gs in self.get_groups_by_application(cr, uid, user_context):
                # hide groups in category 'Hidden' (except to group_no_one)
                attrs = {'groups': 'base.group_no_one'} if app and (app.xml_id == 'base.module_category_hidden' or app.xml_id == 'base.module_category_extra') else {}
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
                        if g == group_no_one:
                            # make the group_no_one invisible in the form view
                            xml2.append(E.field(name=field_name, invisible="1", **attrs))
                        else:
                            xml2.append(E.field(name=field_name, **attrs))

            xml2.append({'class': "o_label_nowrap"})
            xml = E.field(E.group(*(xml1), col="2"), E.group(*(xml2), col="4"), name="groups_id", position="replace")
            xml.addprevious(etree.Comment("GENERATED AUTOMATICALLY BY GROUPS"))
            xml_content = etree.tostring(xml, pretty_print=True, xml_declaration=True, encoding="utf-8")
            view.with_context(context, lang=None).write({'arch': xml_content})
        return True

    def get_application_groups(self, cr, uid, domain=None, context=None):
        if domain is None:
            domain = []
        domain.append(('share', '=', False))
        return self.search(cr, uid, domain, context=context)

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
        values = self._remove_reified_groups(values)
        return super(users_view, self).create(cr, uid, values, context)

    def write(self, cr, uid, ids, values, context=None):
        values = self._remove_reified_groups(values)
        return super(users_view, self).write(cr, uid, ids, values, context)

    def _remove_reified_groups(self, values):
        """ return `values` without reified group fields """
        add, rem = [], []
        values1 = {}

        for key, val in values.iteritems():
            if is_boolean_group(key):
                (add if val else rem).append(get_boolean_group(key))
            elif is_selection_groups(key):
                rem += get_selection_groups(key)
                if val:
                    add.append(val)
            else:
                values1[key] = val

        if 'groups_id' not in values and (add or rem):
            # remove group ids in `rem` and add group ids in `add`
            values1['groups_id'] = zip(repeat(3), rem) + zip(repeat(4), add)

        return values1

    def default_get(self, cr, uid, fields, context=None):
        group_fields, fields = partition(is_reified_group, fields)
        fields1 = (fields + ['groups_id']) if group_fields else fields
        values = super(users_view, self).default_get(cr, uid, fields1, context)
        self._add_reified_groups(group_fields, values)

        # add "default_groups_ref" inside the context to set default value for group_id with xml values
        if 'groups_id' in fields and isinstance(context.get("default_groups_ref"), list):
            groups = []
            ir_model_data = self.pool.get('ir.model.data')
            for group_xml_id in context["default_groups_ref"]:
                group_split = group_xml_id.split('.')
                if len(group_split) != 2:
                    raise UserError(_('Invalid context default_groups_ref value (model.name_id) : "%s"') % group_xml_id)
                try:
                    temp, group_id = ir_model_data.get_object_reference(cr, uid, group_split[0], group_split[1])
                except ValueError:
                    group_id = False
                groups += [group_id]
            values['groups_id'] = groups
        return values

    def read(self, cr, uid, ids, fields=None, context=None, load='_classic_read'):
        # determine whether reified groups fields are required, and which ones
        fields1 = fields or self.fields_get(cr, uid, context=context).keys()
        group_fields, other_fields = partition(is_reified_group, fields1)

        # read regular fields (other_fields); add 'groups_id' if necessary
        drop_groups_id = False
        if group_fields and fields:
            if 'groups_id' not in other_fields:
                other_fields.append('groups_id')
                drop_groups_id = True
        else:
            other_fields = fields

        res = super(users_view, self).read(cr, uid, ids, other_fields, context=context, load=load)

        # post-process result to add reified group fields
        if group_fields:
            for values in (res if isinstance(res, list) else [res]):
                self._add_reified_groups(group_fields, values)
                if drop_groups_id:
                    values.pop('groups_id', None)
        return res

    def _add_reified_groups(self, fields, values):
        """ add the given reified group fields into `values` """
        gids = set(parse_m2m(values.get('groups_id') or []))
        for f in fields:
            if is_boolean_group(f):
                values[f] = get_boolean_group(f) in gids
            elif is_selection_groups(f):
                selected = [gid for gid in get_selection_groups(f) if gid in gids]
                values[f] = selected and selected[-1] or False

    def fields_get(self, cr, uid, allfields=None, context=None, write_access=True, attributes=None):
        res = super(users_view, self).fields_get(cr, uid, allfields, context, write_access, attributes)
        # add reified groups fields
        if not self.pool['res.users']._is_admin(cr, uid, [uid]):
            return res
        for app, kind, gs in self.pool['res.groups'].get_groups_by_application(cr, SUPERUSER_ID, context):
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

    def _default_user_ids(self, cr, uid, context=None):
        if context is None:
            context = {}
        user_model = self.pool['res.users']
        user_ids = context.get('active_model') == 'res.users' and context.get('active_ids') or []
        return [
            (0, 0, {'user_id': user.id, 'user_login': user.login})
            for user in user_model.browse(cr, uid, user_ids, context=context)
        ]

    _defaults = {
        'user_ids': _default_user_ids,
    }

    def change_password_button(self, cr, uid, ids, context=None):
        wizard = self.browse(cr, uid, ids, context=context)[0]
        need_reload = any(uid == user.user_id.id for user in wizard.user_ids)

        line_ids = [user.id for user in wizard.user_ids]
        self.pool.get('change.password.user').change_password_button(cr, uid, line_ids, context=context)

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
        'user_id': fields.many2one('res.users', string='User', required=True, ondelete='cascade'),
        'user_login': fields.char('User Login', readonly=True),
        'new_passwd': fields.char('New Password'),
    }
    _defaults = {
        'new_passwd': '',
    }

    def change_password_button(self, cr, uid, ids, context=None):
        for line in self.browse(cr, uid, ids, context=context):
            line.user_id.write({'password': line.new_passwd})
        # don't keep temporary passwords in the database longer than necessary
        self.write(cr, uid, ids, {'new_passwd': False}, context=context)
