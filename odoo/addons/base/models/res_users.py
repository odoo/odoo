# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import contextlib

import base64
import pytz
import datetime
import ipaddress
import itertools
import logging
import hmac

from collections import defaultdict
from hashlib import sha256
from itertools import chain, repeat
from lxml import etree
from lxml.builder import E
import passlib.context

from odoo import api, fields, models, tools, SUPERUSER_ID, _
from odoo.addons.base.models.ir_model import MODULE_UNINSTALL_FLAG
from odoo.exceptions import AccessDenied, AccessError, UserError, ValidationError
from odoo.http import request
from odoo.osv import expression
from odoo.service.db import check_super
from odoo.tools import partition, collections, frozendict, lazy_property

_logger = logging.getLogger(__name__)

# Only users who can modify the user (incl. the user herself) see the real contents of these fields
USER_PRIVATE_FIELDS = []

DEFAULT_CRYPT_CONTEXT = passlib.context.CryptContext(
    # kdf which can be verified by the context. The default encryption kdf is
    # the first of the list
    ['pbkdf2_sha512', 'plaintext'],
    # deprecated algorithms are still verified as usual, but ``needs_update``
    # will indicate that the stored hash should be replaced by a more recent
    # algorithm. Passlib 1.6 supports an `auto` value which deprecates any
    # algorithm but the default, but Ubuntu LTS only provides 1.5 so far.
    deprecated=['plaintext'],
)

concat = chain.from_iterable

#
# Functions for manipulating boolean and selection pseudo-fields
#
def name_boolean_group(id):
    return 'in_group_' + str(id)

def name_selection_groups(ids):
    return 'sel_groups_' + '_'.join(str(it) for it in ids)

def is_boolean_group(name):
    return name.startswith('in_group_')

def is_selection_groups(name):
    return name.startswith('sel_groups_')

def is_reified_group(name):
    return is_boolean_group(name) or is_selection_groups(name)

def get_boolean_group(name):
    return int(name[9:])

def get_selection_groups(name):
    return [int(v) for v in name[11:].split('_')]

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

class ResUsersLog(models.Model):
    _name = 'res.users.log'
    _order = 'id desc'
    _description = 'Users Log'
    # Currenly only uses the magical fields: create_uid, create_date,
    # for recording logins. To be extended for other uses (chat presence, etc.)


class Users(models.Model):
    """ User class. A res.users record models an OpenERP user and is different
        from an employee.

        res.users class now inherits from res.partner. The partner model is
        used to store the data related to the partner: lang, name, address,
        avatar, ... The user model is now dedicated to technical data.
    """
    _name = "res.users"
    _description = 'Users'
    _inherits = {'res.partner': 'partner_id'}
    _order = 'name, login'
    __uid_cache = defaultdict(dict)             # {dbname: {uid: password}}

    # YTI TODO: Check those fields list
    # User can write on a few of his own fields (but not his groups for example)
    SELF_WRITEABLE_FIELDS = ['signature', 'action_id', 'company_id', 'email', 'name', 'image_1920', 'lang', 'tz']
    # User can read a few of his own fields
    SELF_READABLE_FIELDS = ['signature', 'company_id', 'login', 'email', 'name', 'image_1920', 'image_1024', 'image_512', 'image_256', 'image_128', 'lang', 'tz', 'tz_offset', 'groups_id', 'partner_id', '__last_update', 'action_id']

    def _default_groups(self):
        default_user = self.env.ref('base.default_user', raise_if_not_found=False)
        return (default_user or self.env['res.users']).sudo().groups_id

    partner_id = fields.Many2one('res.partner', required=True, ondelete='restrict', auto_join=True,
        string='Related Partner', help='Partner-related data of the user')
    login = fields.Char(required=True, help="Used to log into the system")
    password = fields.Char(
        compute='_compute_password', inverse='_set_password',
        invisible=True, copy=False,
        help="Keep empty if you don't want the user to be able to connect on the system.")
    new_password = fields.Char(string='Set Password',
        compute='_compute_password', inverse='_set_new_password',
        help="Specify a value only when creating a user or if you're "\
             "changing the user's password, otherwise leave empty. After "\
             "a change of password, the user has to login again.")
    active = fields.Boolean(default=True)
    active_partner = fields.Boolean(related='partner_id.active', readonly=True, string="Partner is Active")
    groups_id = fields.Many2many('res.groups', 'res_groups_users_rel', 'uid', 'gid', string='Groups', default=_default_groups)
    log_ids = fields.One2many('res.users.log', 'create_uid', string='User log entries')
    login_date = fields.Datetime(related='log_ids.create_date', string='Latest authentication', readonly=False)
    # YTI I have a doubt for this one
    share = fields.Boolean(compute='_compute_share', compute_sudo=True, string='Share User', store=True,
         help="External user with limited access, created only for the purpose of sharing data.")
    companies_count = fields.Integer(compute='_compute_companies_count', string="Number of Companies")

    # Special behavior for this field: res.company.search() will only return the companies
    # available to the current user (should be the user's companies?), when the user_preference
    # context is set.
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company.id,
        help='The default company for this user.', context={'user_preference': True})
    company_ids = fields.Many2many('res.company', 'res_company_users_rel', 'user_id', 'cid',
        string='Companies', default=lambda self: self.env.company.ids)

    # overridden inherited fields to bypass access rights, in case you have
    # access to the user but not its corresponding partner
    name = fields.Char(related='partner_id.name', inherited=True, readonly=False)
    email = fields.Char(related='partner_id.email', inherited=True, readonly=False)

    # YTI Those groups could be moved IMO
    accesses_count = fields.Integer('# Access Rights', help='Number of access rights that apply to the current user',
                                    compute='_compute_accesses_count', compute_sudo=True)
    rules_count = fields.Integer('# Record Rules', help='Number of record rules that apply to the current user',
                                 compute='_compute_accesses_count', compute_sudo=True)
    groups_count = fields.Integer('# Groups', help='Number of groups that apply to the current user',
                                  compute='_compute_accesses_count', compute_sudo=True)

    _sql_constraints = [
        ('login_key', 'UNIQUE (login)',  'You can not have two users with the same login !')
    ]

    def init(self):
        cr = self.env.cr

        # allow setting plaintext passwords via SQL and have them
        # automatically encrypted at startup: look for passwords which don't
        # match the "extended" MCF and pass those through passlib.
        # Alternative: iterate on *all* passwords and use CryptContext.identify
        cr.execute("""
        SELECT id, password FROM res_users
        WHERE password IS NOT NULL
          AND password !~ '^\$[^$]+\$[^$]+\$.'
        """)
        if self.env.cr.rowcount:
            Users = self.sudo()
            for uid, pw in cr.fetchall():
                Users.browse(uid).password = pw

    def _set_password(self):
        ctx = self._crypt_context()
        hash_password = ctx.hash if hasattr(ctx, 'hash') else ctx.encrypt
        for user in self:
            self._set_encrypted_password(user.id, hash_password(user.password))

    def _set_encrypted_password(self, uid, pw):
        assert self._crypt_context().identify(pw) != 'plaintext'

        self.env.cr.execute(
            'UPDATE res_users SET password=%s WHERE id=%s',
            (pw, uid)
        )
        self.invalidate_cache(['password'], [uid])

    def _check_credentials(self, password):
        """ Validates the current user's password.

        Override this method to plug additional authentication methods.

        Overrides should:

        * call `super` to delegate to parents for credentials-checking
        * catch AccessDenied and perform their own checking
        * (re)raise AccessDenied if the credentials are still invalid
          according to their own validation method

        When trying to check for credentials validity, call _check_credentials
        instead.
        """
        """ Override this method to plug additional authentication methods"""
        assert password
        self.env.cr.execute(
            "SELECT COALESCE(password, '') FROM res_users WHERE id=%s",
            [self.env.user.id]
        )
        [hashed] = self.env.cr.fetchone()
        valid, replacement = self._crypt_context()\
            .verify_and_update(password, hashed)
        if replacement is not None:
            self._set_encrypted_password(self.env.user.id, replacement)
        if not valid:
            raise AccessDenied()

    def _compute_password(self):
        for user in self:
            user.password = ''
            user.new_password = ''

    def _set_new_password(self):
        for user in self:
            if not user.new_password:
                # Do not update the password if no value is provided, ignore silently.
                # For example web client submits False values for all empty fields.
                continue
            if user == self.env.user:
                # To change their own password, users must use the client-specific change password wizard,
                # so that the new password is immediately used for further RPC requests, otherwise the user
                # will face unexpected 'Access Denied' exceptions.
                raise UserError(_('Please use the change password wizard (in User Preferences or User menu) to change your own password.'))
            else:
                user.password = user.new_password

    @api.depends('groups_id')
    def _compute_share(self):
        for user in self:
            user.share = not user.has_group('base.group_user')

    def _compute_companies_count(self):
        self.companies_count = self.env['res.company'].sudo().search_count([])

    @api.depends('groups_id')
    def _compute_accesses_count(self):
        for user in self:
            groups = user.groups_id
            user.accesses_count = len(groups.model_access)
            user.rules_count = len(groups.rule_groups)
            user.groups_count = len(groups)

    @api.onchange('login')
    def on_change_login(self):
        if self.login and tools.single_email_re.match(self.login):
            self.email = self.login

    def _read(self, fields):
        super(Users, self)._read(fields)
        canwrite = self.check_access_rights('write', raise_exception=False)
        if not canwrite and set(USER_PRIVATE_FIELDS).intersection(fields):
            for record in self:
                for f in USER_PRIVATE_FIELDS:
                    try:
                        record._cache[f]
                        record._cache[f] = '********'
                    except Exception:
                        # skip SpecialValue (e.g. for missing record or access right)
                        pass

    @api.constrains('company_id', 'company_ids')
    def _check_company(self):
        if any(user.company_id not in user.company_ids for user in self):
            raise ValidationError(_('The chosen company is not in the allowed companies for this user'))

    @api.constrains('groups_id')
    def _check_one_user_type(self):
        """We check that no users are both portal and users (same with public).
           This could typically happen because of implied groups.
        """
        user_types_category = self.env.ref('base.module_category_user_type', raise_if_not_found=False)
        user_types_groups = self.env['res.groups'].search(
            [('category_id', '=', user_types_category.id)]) if user_types_category else False
        if user_types_groups:  # needed at install
            if self._has_multiple_groups(user_types_groups.ids):
                raise ValidationError(_('The user cannot have more than one user types.'))

    def _has_multiple_groups(self, group_ids):
        """The method is not fast if the list of ids is very long;
           so we rather check all users than limit to the size of the group
        :param group_ids: list of group ids
        :return: boolean: is there at least a user in at least 2 of the provided groups
        """
        if group_ids:
            args = [tuple(group_ids)]
            if len(self.ids) == 1:
                where_clause = "AND r.uid = %s"
                args.append(self.id)
            else:
                where_clause = ""  # default; we check ALL users (actually pretty efficient)
            query = """
                    SELECT 1 FROM res_groups_users_rel WHERE EXISTS(
                        SELECT r.uid
                        FROM res_groups_users_rel r
                        WHERE r.gid IN %s""" + where_clause + """
                        GROUP BY r.uid HAVING COUNT(r.gid) > 1
                    )
            """
            self.env.cr.execute(query, args)
            return bool(self.env.cr.fetchall())
        else:
            return False

    def toggle_active(self):
        for user in self:
            if not user.active and not user.partner_id.active:
                user.partner_id.toggle_active()
        super(Users, self).toggle_active()

    def read(self, fields=None, load='_classic_read'):
        if fields and self == self.env.user:
            for key in fields:
                if not (key in self.SELF_READABLE_FIELDS or key.startswith('context_')):
                    break
            else:
                # safe fields only, so we read as super-user to bypass access rights
                self = self.sudo()

        return super(Users, self).read(fields=fields, load=load)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        groupby_fields = set([groupby] if isinstance(groupby, str) else groupby)
        if groupby_fields.intersection(USER_PRIVATE_FIELDS):
            raise AccessError(_("Invalid 'group by' parameter"))
        return super(Users, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        if not self.env.su and args:
            domain_fields = {term[0] for term in args if isinstance(term, (tuple, list))}
            if domain_fields.intersection(USER_PRIVATE_FIELDS):
                raise AccessError(_('Invalid search criterion'))
        return super(Users, self)._search(args, offset=offset, limit=limit, order=order, count=count,
                                          access_rights_uid=access_rights_uid)

    @api.model_create_multi
    def create(self, vals_list):
        users = super(Users, self).create(vals_list)
        for user in users:
            # if partner is global we keep it that way
            if user.partner_id.company_id:
                user.partner_id.company_id = user.company_id
            user.partner_id.active = user.active
        return users

    def write(self, values):
        if values.get('active') and SUPERUSER_ID in self._ids:
            raise UserError(_("You cannot activate the superuser."))
        if values.get('active') == False and self._uid in self._ids:
            raise UserError(_("You cannot deactivate the user you're currently logged in as."))

        if values.get('active'):
            for user in self:
                if not user.active and not user.partner_id.active:
                    user.partner_id.toggle_active()
        if self == self.env.user:
            for key in list(values):
                if not (key in self.SELF_WRITEABLE_FIELDS or key.startswith('context_')):
                    break
            else:
                if 'company_id' in values:
                    if values['company_id'] not in self.env.user.company_ids.ids:
                        del values['company_id']
                # safe fields only, so we write as super-user to bypass access rights
                self = self.sudo().with_context(binary_field_real_user=self.env.user)

        res = super(Users, self).write(values)
        if 'company_id' in values:
            for user in self:
                # if partner is global we keep it that way
                if user.partner_id.company_id and user.partner_id.company_id.id != values['company_id']:
                    user.partner_id.write({'company_id': user.company_id.id})

        if 'company_id' in values or 'company_ids' in values:
            # Reset lazy properties `company` & `companies` on all envs
            # This is unlikely in a business code to change the company of a user and then do business stuff
            # but in case it happens this is handled.
            # e.g. `account_test_savepoint.py` `setup_company_data`, triggered by `test_account_invoice_report.py`
            for env in list(self.env.envs):
                if env.user in self:
                    lazy_property.reset_all(env)

        # clear caches linked to the users
        if self.ids and 'groups_id' in values:
            # DLE P139: Calling invalidate_cache on a new, well you lost everything as you wont be able to take it back from the cache
            # `test_00_equipment_multicompany_user`
            self.env['ir.model.access'].call_cache_clearing_methods()
            self.env['ir.rule'].clear_caches()
            self.has_group.clear_cache(self)
        if any(key.startswith('context_') or key in ('lang', 'tz') for key in values):
            self.context_get.clear_cache(self)
        if any(key in values for key in ['active'] + USER_PRIVATE_FIELDS):
            db = self._cr.dbname
            for id in self.ids:
                self.__uid_cache[db].pop(id, None)
        if any(key in values for key in self._get_session_token_fields()):
            self._invalidate_session_cache()

        return res

    def unlink(self):
        if SUPERUSER_ID in self.ids:
            raise UserError(_('You can not remove the admin user as it is used internally for resources created by Odoo (updates, module installation, ...)'))
        db = self._cr.dbname
        for id in self.ids:
            self.__uid_cache[db].pop(id, None)
        self._invalidate_session_cache()
        return super(Users, self).unlink()

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        user_ids = []
        if operator not in expression.NEGATIVE_TERM_OPERATORS:
            if operator == 'ilike' and not (name or '').strip():
                domain = []
            else:
                domain = [('login', '=', name)]
            user_ids = self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)
        if not user_ids:
            user_ids = self._search(expression.AND([[('name', operator, name)], args]), limit=limit, access_rights_uid=name_get_uid)
        return models.lazy_name_get(self.browse(user_ids).with_user(name_get_uid))

    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {})
        if ('name' not in default) and ('partner_id' not in default):
            default['name'] = _("%s (copy)") % self.name
        if 'login' not in default:
            default['login'] = _("%s (copy)") % self.login
        return super(Users, self).copy(default)

    @api.model
    @tools.ormcache('self._uid')
    def context_get(self):
        user = self.env.user
        # determine field names to read
        name_to_key = {
            name: name[8:] if name.startswith('context_') else name
            for name in self._fields
            if name.startswith('context_') or name in ('lang', 'tz')
        }
        # use read() to not read other fields: this must work while modifying
        # the schema of models res.users or res.partner
        values = user.read(list(name_to_key), load=False)[0]
        return frozendict({
            key: values[name]
            for name, key in name_to_key.items()
        })

    @api.model
    def action_get(self):
        return self.sudo().env.ref('base.action_res_users_my').read()[0]

    def check_super(self, passwd):
        return check_super(passwd)

    @api.model
    def _update_last_login(self):
        # only create new records to avoid any side-effect on concurrent transactions
        # extra records will be deleted by the periodical garbage collection
        self.env['res.users.log'].create({}) # populated by defaults

    @api.model
    def _get_login_domain(self, login):
        return [('login', '=', login)]

    @api.model
    def _get_login_order(self):
        return self._order

    @classmethod
    def _login(cls, db, login, password):
        if not password:
            raise AccessDenied()
        ip = request.httprequest.environ['REMOTE_ADDR'] if request else 'n/a'
        try:
            with cls.pool.cursor() as cr:
                self = api.Environment(cr, SUPERUSER_ID, {})[cls._name]
                with self._assert_can_auth():
                    user = self.search(self._get_login_domain(login), order=self._get_login_order(), limit=1)
                    if not user:
                        raise AccessDenied()
                    user = user.with_user(user)
                    user._check_credentials(password)
                    user._update_last_login()
        except AccessDenied:
            _logger.info("Login failed for db:%s login:%s from %s", db, login, ip)
            raise

        _logger.info("Login successful for db:%s login:%s from %s", db, login, ip)

        return user.id

    @classmethod
    def authenticate(cls, db, login, password, user_agent_env):
        """Verifies and returns the user ID corresponding to the given
          ``login`` and ``password`` combination, or False if there was
          no matching user.
           :param str db: the database on which user is trying to authenticate
           :param str login: username
           :param str password: user password
           :param dict user_agent_env: environment dictionary describing any
               relevant environment attributes
        """
        uid = cls._login(db, login, password)
        if user_agent_env and user_agent_env.get('base_location'):
            with cls.pool.cursor() as cr:
                env = api.Environment(cr, uid, {})
                if env.user.has_group('base.group_system'):
                    # Successfully logged in as system user!
                    # Attempt to guess the web base url...
                    try:
                        base = user_agent_env['base_location']
                        ICP = env['ir.config_parameter']
                        if not ICP.get_param('web.base.url.freeze'):
                            ICP.set_param('web.base.url', base)
                    except Exception:
                        _logger.exception("Failed to update web.base.url configuration parameter")
        return uid

    @classmethod
    def check(cls, db, uid, passwd):
        """Verifies that the given (uid, password) is authorized for the database ``db`` and
           raise an exception if it is not."""
        if not passwd:
            # empty passwords disallowed for obvious security reasons
            raise AccessDenied()
        db = cls.pool.db_name
        if cls.__uid_cache[db].get(uid) == passwd:
            return
        cr = cls.pool.cursor()
        try:
            self = api.Environment(cr, uid, {})[cls._name]
            with self._assert_can_auth():
                self._check_credentials(passwd)
                cls.__uid_cache[db][uid] = passwd
        finally:
            cr.close()

    def _get_session_token_fields(self):
        return {'id', 'login', 'password', 'active'}

    @tools.ormcache('sid')
    def _compute_session_token(self, sid):
        """ Compute a session token given a session id and a user id """
        # retrieve the fields used to generate the session token
        session_fields = ', '.join(sorted(self._get_session_token_fields()))
        self.env.cr.execute("""SELECT %s, (SELECT value FROM ir_config_parameter WHERE key='database.secret')
                                FROM res_users
                                WHERE id=%%s""" % (session_fields), (self.id,))
        if self.env.cr.rowcount != 1:
            self._invalidate_session_cache()
            return False
        data_fields = self.env.cr.fetchone()
        # generate hmac key
        key = (u'%s' % (data_fields,)).encode('utf-8')
        # hmac the session id
        data = sid.encode('utf-8')
        h = hmac.new(key, data, sha256)
        # keep in the cache the token
        return h.hexdigest()

    def _invalidate_session_cache(self):
        """ Clear the sessions cache """
        self._compute_session_token.clear_cache(self)

    @api.model
    def change_password(self, old_passwd, new_passwd):
        """Change current user password. Old password must be provided explicitly
        to prevent hijacking an existing user session, or for cases where the cleartext
        password is not used to authenticate requests.

        :return: True
        :raise: odoo.exceptions.AccessDenied when old password is wrong
        :raise: odoo.exceptions.UserError when new password is not set or empty
        """
        self.check(self._cr.dbname, self._uid, old_passwd)
        if new_passwd:
            # use self.env.user here, because it has uid=SUPERUSER_ID
            return self.env.user.write({'password': new_passwd})
        raise UserError(_("Setting empty passwords is not allowed for security reasons!"))

    def preference_save(self):
        return {
            'type': 'ir.actions.client',
            'tag': 'reload_context',
        }

    def preference_change_password(self):
        return {
            'type': 'ir.actions.client',
            'tag': 'change_password',
            'target': 'new',
        }

    @api.model
    def has_group(self, group_ext_id):
        # use singleton's id if called on a non-empty recordset, otherwise
        # context uid
        uid = self.id or self._uid
        return self.with_user(uid)._has_group(group_ext_id)

    @api.model
    @tools.ormcache('self._uid', 'group_ext_id')
    def _has_group(self, group_ext_id):
        """Checks whether user belongs to given group.

        :param str group_ext_id: external ID (XML ID) of the group.
           Must be provided in fully-qualified form (``module.ext_id``), as there
           is no implicit module to use..
        :return: True if the current user is a member of the group with the
           given external ID (XML ID), else False.
        """
        assert group_ext_id and '.' in group_ext_id, "External ID '%s' must be fully qualified" % group_ext_id
        module, ext_id = group_ext_id.split('.')
        self._cr.execute("""SELECT 1 FROM res_groups_users_rel WHERE uid=%s AND gid IN
                            (SELECT res_id FROM ir_model_data WHERE module=%s AND name=%s)""",
                         (self._uid, module, ext_id))
        return bool(self._cr.fetchone())
    # for a few places explicitly clearing the has_group cache
    has_group.clear_cache = _has_group.clear_cache

    def action_show_groups(self):
        self.ensure_one()
        return {
            'name': _('Groups'),
            'view_mode': 'tree,form',
            'res_model': 'res.groups',
            'type': 'ir.actions.act_window',
            'context': {'create': False, 'delete': False},
            'domain': [('id','in', self.groups_id.ids)],
            'target': 'current',
        }

    def action_show_accesses(self):
        self.ensure_one()
        return {
            'name': _('Access Rights'),
            'view_mode': 'tree,form',
            'res_model': 'ir.model.access',
            'type': 'ir.actions.act_window',
            'context': {'create': False, 'delete': False},
            'domain': [('id', 'in', self.groups_id.model_access.ids)],
            'target': 'current',
        }

    def action_show_rules(self):
        self.ensure_one()
        return {
            'name': _('Record Rules'),
            'view_mode': 'tree,form',
            'res_model': 'ir.rule',
            'type': 'ir.actions.act_window',
            'context': {'create': False, 'delete': False},
            'domain': [('id', 'in', self.groups_id.rule_groups.ids)],
            'target': 'current',
        }

    def _is_public(self):
        self.ensure_one()
        return self.has_group('base.group_public')

    def _is_system(self):
        self.ensure_one()
        return self.has_group('base.group_system')

    def _is_admin(self):
        self.ensure_one()
        return self._is_superuser() or self.has_group('base.group_erp_manager')

    def _is_superuser(self):
        self.ensure_one()
        return self.id == SUPERUSER_ID

    @api.model
    def get_company_currency_id(self):
        return self.env.company.currency_id.id

    def _crypt_context(self):
        """ Passlib CryptContext instance used to encrypt and verify
        passwords. Can be overridden if technical, legal or political matters
        require different kdfs than the provided default.

        Requires a CryptContext as deprecation and upgrade notices are used
        internally
        """
        return DEFAULT_CRYPT_CONTEXT

    @contextlib.contextmanager
    def _assert_can_auth(self):
        """ Checks that the current environment even allows the current auth
        request to happen.

        The baseline implementation is a simple linear login cooldown: after
        a number of failures trying to log-in, the user (by login) is put on
        cooldown. During the cooldown period, login *attempts* are ignored
        and logged.

        .. warning::

            The login counter is not shared between workers and not
            specifically thread-safe, the feature exists mostly for
            rate-limiting on large number of login attempts (brute-forcing
            passwords) so that should not be much of an issue.

            For a more complex strategy (e.g. database or distribute storage)
            override this method. To simply change the cooldown criteria
            (configuration, ...) override _on_login_cooldown instead.

        .. note::

            This is a *context manager* so it can be called around the login
            procedure without having to call it itself.
        """
        # needs request for remote address
        if not request:
            yield
            return

        reg = self.env.registry
        failures_map = getattr(reg, '_login_failures', None)
        if failures_map is None:
            failures_map = reg._login_failures = collections.defaultdict(lambda : (0, datetime.datetime.min))

        source = request.httprequest.remote_addr
        (failures, previous) = failures_map[source]
        if self._on_login_cooldown(failures, previous):
            _logger.warning(
                "Login attempt ignored for %s on %s: "
                "%d failures since last success, last failure at %s. "
                "You can configure the number of login failures before a "
                "user is put on cooldown as well as the duration in the "
                "System Parameters. Disable this feature by setting "
                "\"base.login_cooldown_after\" to 0.",
                source, self.env.cr.dbname, failures, previous)
            if ipaddress.ip_address(source).is_private:
                _logger.warning(
                    "The rate-limited IP address %s is classified as private "
                    "and *might* be a proxy. If your Odoo is behind a proxy, "
                    "it may be mis-configured. Check that you are running "
                    "Odoo in Proxy Mode and that the proxy is properly configured, see "
                    "https://www.odoo.com/documentation/13.0/setup/deploy.html#https for details.",
                    source
                )
            raise AccessDenied(_("Too many login failures, please wait a bit before trying again."))

        try:
            yield
        except AccessDenied:
            (failures, __) = reg._login_failures[source]
            reg._login_failures[source] = (failures + 1, datetime.datetime.now())
            raise
        else:
            reg._login_failures.pop(source, None)

    def _on_login_cooldown(self, failures, previous):
        """ Decides whether the user trying to log in is currently
        "on cooldown" and not even allowed to attempt logging in.

        The default cooldown function simply puts the user on cooldown for
        <login_cooldown_duration> seconds after each failure following the
        <login_cooldown_after>th (0 to disable).

        Can be overridden to implement more complex backoff strategies, or
        e.g. wind down or reset the cooldown period as the previous failure
        recedes into the far past.

        :param int failures: number of recorded failures (since last success)
        :param previous: timestamp of previous failure
        :type previous:  datetime.datetime
        :returns: whether the user is currently in cooldown phase (true if cooldown, false if no cooldown and login can continue)
        :rtype: bool
        """
        cfg = self.env['ir.config_parameter'].sudo()
        min_failures = int(cfg.get_param('base.login_cooldown_after', 5))
        if min_failures == 0:
            return False

        delay = int(cfg.get_param('base.login_cooldown_duration', 60))
        return failures >= min_failures and (datetime.datetime.now() - previous) < datetime.timedelta(seconds=delay)

    def _register_hook(self):
        if hasattr(self, 'check_credentials'):
            _logger.warning("The check_credentials method of res.users has been renamed _check_credentials. One of your installed modules defines one, but it will not be called anymore.")

    def _get_placeholder_filename(self, field=None):
        image_fields = ['image_%s' % size for size in [1920, 1024, 512, 256, 128]]
        if field in image_fields and not self:
            return 'base/static/img/user-slash.png'
        return super()._get_placeholder_filename(field=field)

class UsersImplied(models.Model):
    _inherit = 'res.users'

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if 'groups_id' in values:
                # complete 'groups_id' with implied groups
                user = self.new(values)
                gs = user.groups_id._origin
                gs = gs | gs.trans_implied_ids
                values['groups_id'] = type(self).groups_id.convert_to_write(gs, user)
        return super(UsersImplied, self).create(vals_list)

    def write(self, values):
        users_before = self.filtered(lambda u: u.has_group('base.group_user'))
        res = super(UsersImplied, self).write(values)
        if values.get('groups_id'):
            # add implied groups for all users
            for user in self:
                if not user.has_group('base.group_user') and user in users_before:
                    # if we demoted a user, we strip him of all its previous privileges
                    # (but we should not do it if we are simply adding a technical group to a portal user)
                    vals = {'groups_id': [(5, 0, 0)] + values['groups_id']}
                    super(UsersImplied, user).write(vals)
                gs = set(concat(g.trans_implied_ids for g in user.groups_id))
                vals = {'groups_id': [(4, g.id) for g in gs]}
                super(UsersImplied, user).write(vals)
        return res


class UsersView(models.Model):
    _inherit = 'res.users'

    @api.model
    def create(self, values):
        values = self._remove_reified_groups(values)
        user = super(UsersView, self).create(values)
        group_multi_company = self.env.ref('base.group_multi_company', False)
        if group_multi_company and 'company_ids' in values:
            if len(user.company_ids) <= 1 and user.id in group_multi_company.users.ids:
                user.write({'groups_id': [(3, group_multi_company.id)]})
            elif len(user.company_ids) > 1 and user.id not in group_multi_company.users.ids:
                user.write({'groups_id': [(4, group_multi_company.id)]})
        return user

    def write(self, values):
        values = self._remove_reified_groups(values)
        res = super(UsersView, self).write(values)
        group_multi_company = self.env.ref('base.group_multi_company', False)
        if group_multi_company and 'company_ids' in values:
            for user in self:
                if len(user.company_ids) <= 1 and user.id in group_multi_company.users.ids:
                    user.write({'groups_id': [(3, group_multi_company.id)]})
                elif len(user.company_ids) > 1 and user.id not in group_multi_company.users.ids:
                    user.write({'groups_id': [(4, group_multi_company.id)]})
        return res

    @api.model
    def new(self, values={}, origin=None, ref=None):
        values = self._remove_reified_groups(values)
        user = super().new(values=values, origin=origin, ref=ref)
        group_multi_company = self.env.ref('base.group_multi_company', False)
        if group_multi_company and 'company_ids' in values:
            if len(user.company_ids) <= 1 and user.id in group_multi_company.users.ids:
                user.update({'groups_id': [(3, group_multi_company.id)]})
            elif len(user.company_ids) > 1 and user.id not in group_multi_company.users.ids:
                user.update({'groups_id': [(4, group_multi_company.id)]})
        return user

    def _remove_reified_groups(self, values):
        """ return `values` without reified group fields """
        add, rem = [], []
        values1 = {}

        for key, val in values.items():
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
            values1['groups_id'] = list(itertools.chain(
                zip(repeat(3), rem),
                zip(repeat(4), add)
            ))

        return values1

    @api.model
    def default_get(self, fields):
        group_fields, fields = partition(is_reified_group, fields)
        fields1 = (fields + ['groups_id']) if group_fields else fields
        values = super(UsersView, self).default_get(fields1)
        self._add_reified_groups(group_fields, values)
        return values

    def read(self, fields=None, load='_classic_read'):
        # determine whether reified groups fields are required, and which ones
        fields1 = fields or list(self.fields_get())
        group_fields, other_fields = partition(is_reified_group, fields1)

        # read regular fields (other_fields); add 'groups_id' if necessary
        drop_groups_id = False
        if group_fields and fields:
            if 'groups_id' not in other_fields:
                other_fields.append('groups_id')
                drop_groups_id = True
        else:
            other_fields = fields

        res = super(UsersView, self).read(other_fields, load=load)

        # post-process result to add reified group fields
        if group_fields:
            for values in res:
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
                # if 'Internal User' is in the group, this is the "User Type" group
                # and we need to show 'Internal User' selected, not Public/Portal.
                if self.env.ref('base.group_user').id in selected:
                    values[f] = self.env.ref('base.group_user').id
                else:
                    values[f] = selected and selected[-1] or False

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super(UsersView, self).fields_get(allfields, attributes=attributes)
        # add reified groups fields
        for app, kind, gs, category_name in self.env['res.groups'].sudo().get_groups_by_application():
            if kind == 'selection':
                # 'User Type' should not be 'False'. A user is either 'employee', 'portal' or 'public' (required).
                selection_vals = [(False, '')]
                if app.xml_id == 'base.module_category_user_type':
                    selection_vals = []
                field_name = name_selection_groups(gs.ids)
                if allfields and field_name not in allfields:
                    continue
                # selection group field
                tips = ['%s: %s' % (g.name, g.comment) for g in gs if g.comment]
                res[field_name] = {
                    'type': 'selection',
                    'string': app.name or _('Other'),
                    'selection': selection_vals + [(g.id, g.name) for g in gs],
                    'help': '\n'.join(tips),
                    'exportable': False,
                    'selectable': False,
                }
            else:
                # boolean group fields
                for g in gs:
                    field_name = name_boolean_group(g.id)
                    if allfields and field_name not in allfields:
                        continue
                    res[field_name] = {
                        'type': 'boolean',
                        'string': g.name,
                        'help': g.comment,
                        'exportable': False,
                        'selectable': False,
                    }
        return res
