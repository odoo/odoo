# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import contextlib

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

from odoo import api, fields, models, tools, SUPERUSER_ID, ADMINUSER_ID, _
from odoo.exceptions import AccessDenied, AccessError, UserError, ValidationError
from odoo.http import request
from odoo.osv import expression
from odoo.service.db import check_super
from odoo.tools import partition, pycompat, collections

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
# Functions for manipulating boolean and selection fields
#


def is_boolean_group(name):
    return name.startswith('has_group_')


def is_selection_groups(name):
    return name.startswith('group_')


#----------------------------------------------------------
# Basic res.groups and res.users
#----------------------------------------------------------


class Groups(models.Model):
    _name = "res.groups"
    _description = "Access Groups"
    _rec_name = 'full_name'
    _order = 'name'

    name = fields.Char(required=True, translate=True)
    users = fields.Many2many('res.users', 'res_groups_users_rel', 'gid', 'uid')
    model_access = fields.One2many('ir.model.access', 'group_id', string='Access Controls', copy=True)
    rule_groups = fields.Many2many('ir.rule', 'rule_group_rel',
        'group_id', 'rule_group_id', string='Rules', domain=[('global', '=', False)])
    menu_access = fields.Many2many('ir.ui.menu', 'ir_ui_menu_group_rel', 'gid', 'menu_id', string='Access Menu')
    view_access = fields.Many2many('ir.ui.view', 'ir_ui_view_group_rel', 'group_id', 'view_id', string='Views')
    comment = fields.Text(translate=True)
    category_id = fields.Many2one('ir.module.category', string='Application', index=True)
    color = fields.Integer(string='Color Index')
    full_name = fields.Char(compute='_compute_full_name', string='Group Name', search='_search_full_name')
    share = fields.Boolean(string='Share Group', help="Group created to set access rights for sharing data with some users.")

    _sql_constraints = [
        ('name_uniq', 'unique (category_id, name)', 'The name of the group must be unique within an application!')
    ]

    @api.depends('category_id.name', 'name')
    def _compute_full_name(self):
        # Important: value must be stored in environment of group, not group1!
        for group, group1 in pycompat.izip(self, self.sudo()):
            if group1.category_id:
                group.full_name = '%s / %s' % (group1.category_id.name, group1.name)
            else:
                group.full_name = group1.name

    def _search_full_name(self, operator, operand):
        lst = True
        if isinstance(operand, bool):
            domains = [[('name', operator, operand)], [('category_id.name', operator, operand)]]
            if operator in expression.NEGATIVE_TERM_OPERATORS == (not operand):
                return expression.AND(domains)
            else:
                return expression.OR(domains)
        if isinstance(operand, pycompat.string_types):
            lst = False
            operand = [operand]
        where = []
        for group in operand:
            values = [v for v in group.split('/') if v]
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

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        # add explicit ordering if search is sorted on full_name
        if order and order.startswith('full_name'):
            groups = super(Groups, self).search(args)
            groups = groups.sorted('full_name', reverse=order.endswith('DESC'))
            groups = groups[offset:offset+limit] if limit else groups[offset:]
            return len(groups) if count else groups.ids
        return super(Groups, self)._search(args, offset=offset, limit=limit, order=order, count=count, access_rights_uid=access_rights_uid)

    @api.multi
    def copy(self, default=None):
        self.ensure_one()
        chosen_name = default.get('name') if default else ''
        default_name = chosen_name or _('%s (copy)') % self.name
        default = dict(default or {}, name=default_name)
        return super(Groups, self).copy(default)

    @api.multi
    def write(self, vals):
        if 'name' in vals:
            if vals['name'].startswith('-'):
                raise UserError(_('The name of the group can not start with "-"'))
        # invalidate caches before updating groups, since the recomputation of
        # field 'share' depends on method has_group()
        self.env['ir.model.access'].call_cache_clearing_methods()
        self.env['res.users'].has_group.clear_cache(self.env['res.users'])
        return super(Groups, self).write(vals)


class ResUsersLog(models.Model):
    _name = 'res.users.log'
    _order = 'id desc'
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

    # User can write on a few of his own fields (but not his groups for example)
    SELF_WRITEABLE_FIELDS = ['signature', 'action_id', 'company_id', 'email', 'name', 'image', 'image_medium', 'image_small', 'lang', 'tz']
    # User can read a few of his own fields
    SELF_READABLE_FIELDS = ['signature', 'company_id', 'login', 'email', 'name', 'image', 'image_medium', 'image_small', 'lang', 'tz', 'tz_offset', 'groups_id', 'partner_id', '__last_update', 'action_id']

    def _default_groups(self):
        default_user = self.env.ref('base.default_user', raise_if_not_found=False)
        return (default_user or self.env['res.users']).sudo().groups_id

    def _companies_count(self):
        return self.env['res.company'].sudo().search_count([])

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
    signature = fields.Html()
    active = fields.Boolean(default=True)
    action_id = fields.Many2one('ir.actions.actions', string='Home Action',
        help="If specified, this action will be opened at log on for this user, in addition to the standard menu.")
    groups_id = fields.Many2many('res.groups', 'res_groups_users_rel', 'uid', 'gid', string='Groups', default=_default_groups)
    log_ids = fields.One2many('res.users.log', 'create_uid', string='User log entries')
    login_date = fields.Datetime(related='log_ids.create_date', string='Latest connection')
    share = fields.Boolean(compute='_compute_share', compute_sudo=True, string='Share User', store=True,
         help="External user with limited access, created only for the purpose of sharing data.")
    companies_count = fields.Integer(compute='_compute_companies_count', string="Number of Companies", default=_companies_count)
    tz_offset = fields.Char(compute='_compute_tz_offset', string='Timezone offset', invisible=True)

    @api.model
    def _get_company(self):
        return self.env.user.company_id

    # Special behavior for this field: res.company.search() will only return the companies
    # available to the current user (should be the user's companies?), when the user_preference
    # context is set.
    company_id = fields.Many2one('res.company', string='Company', required=True, default=_get_company,
        help='The company this user is currently working for.', context={'user_preference': True})
    company_ids = fields.Many2many('res.company', 'res_company_users_rel', 'user_id', 'cid',
        string='Companies', default=_get_company)

    # overridden inherited fields to bypass access rights, in case you have
    # access to the user but not its corresponding partner
    name = fields.Char(related='partner_id.name', inherited=True)
    email = fields.Char(related='partner_id.email', inherited=True)

    group_base_user = fields.Selection(
        selection=lambda self: self._get_group_selection('base.module_category_user_type'),
        string="User type", compute='_compute_groups_id', inverse='_inverse_groups_id',
        category_xml_id='base.module_category_user_type')

    group_administration_user = fields.Selection(
        selection=lambda self: self._get_group_selection('base.module_category_administration'),
        string="Administration", compute='_compute_groups_id', inverse='_inverse_groups_id',
        category_xml_id='base.module_category_administration')

    has_group_multi_company = fields.Boolean(
        'Multi Companies', compute='_compute_groups_id', inverse='_inverse_groups_id',
        group_xml_id='base.group_multi_company')

    has_group_multi_currency = fields.Boolean(
        'Multi Currencies', compute='_compute_groups_id', inverse='_inverse_groups_id',
        group_xml_id='base.group_multi_currency')

    has_group_no_one = fields.Boolean(
        'Technical Features', compute='_compute_groups_id', inverse='_inverse_groups_id',
        group_xml_id='base.group_no_one')

    has_group_partner_manager = fields.Boolean(
        'Contact Creation', compute='_compute_groups_id', inverse='_inverse_groups_id',
        group_xml_id='base.group_partner_manager')

    has_group_private_addresses = fields.Boolean(
        'Access to Private Addresses', compute='_compute_groups_id', inverse='_inverse_groups_id',
        group_xml_id='base.group_private_addresses')

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
        for user in self:
            self._set_encrypted_password(user.id, ctx.encrypt(user.password))

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

    @api.multi
    def _compute_companies_count(self):
        companies_count = self._companies_count()
        for user in self:
            user.companies_count = companies_count

    @api.depends('tz')
    def _compute_tz_offset(self):
        for user in self:
            user.tz_offset = datetime.datetime.now(pytz.timezone(user.tz or 'GMT')).strftime('%z')

    @api.onchange('login')
    def on_change_login(self):
        if self.login and tools.single_email_re.match(self.login):
            self.email = self.login

    @api.onchange('parent_id')
    def onchange_parent_id(self):
        return self.mapped('partner_id').onchange_parent_id()

    def _read_from_database(self, field_names, inherited_field_names=[]):
        super(Users, self)._read_from_database(field_names, inherited_field_names)
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

    @api.multi
    @api.constrains('company_id', 'company_ids')
    def _check_company(self):
        if any(user.company_ids and user.company_id not in user.company_ids for user in self):
            raise ValidationError(_('The chosen company is not in the allowed companies for this user'))

    @api.multi
    @api.constrains('action_id')
    def _check_action_id(self):
        action_open_website = self.env.ref('base.action_open_website', raise_if_not_found=False)
        if action_open_website and any(user.action_id.id == action_open_website.id for user in self):
            raise ValidationError(_('The "App Switcher" action cannot be selected as home action.'))

    @api.multi
    def toggle_active(self):
        for user in self:
            if not user.active and not user.partner_id.active:
                user.partner_id.toggle_active()
        super(Users, self).toggle_active()

    @api.multi
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
        groupby_fields = set([groupby] if isinstance(groupby, pycompat.string_types) else groupby)
        if groupby_fields.intersection(USER_PRIVATE_FIELDS):
            raise AccessError(_("Invalid 'group by' parameter"))
        return super(Users, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        if self._uid != SUPERUSER_ID and args:
            domain_fields = {term[0] for term in args if isinstance(term, (tuple, list))}
            if domain_fields.intersection(USER_PRIVATE_FIELDS):
                raise AccessError(_('Invalid search criterion'))
        return super(Users, self)._search(args, offset=offset, limit=limit, order=order, count=count,
                                          access_rights_uid=access_rights_uid)

    @api.model_create_multi
    def create(self, vals_list):
        users = super(Users, self.with_context(default_customer=False)).create(vals_list)
        for user in users:
            user.partner_id.active = user.active
            if user.partner_id.company_id:
                user.partner_id.write({'company_id': user.company_id.id})
        return users

    @api.multi
    def write(self, values):
        if values.get('active') == False:
            for user in self:
                if user.id == SUPERUSER_ID:
                    raise UserError(_("You cannot deactivate the admin user."))
                elif user.id == self._uid:
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
                self = self.sudo()

        res = super(Users, self).write(values)
        if 'company_id' in values:
            for user in self:
                # if partner is global we keep it that way
                if user.partner_id.company_id and user.partner_id.company_id.id != values['company_id']:
                    user.partner_id.write({'company_id': user.company_id.id})
            # clear default ir values when company changes
            self.env['ir.default'].clear_caches()

        # clear caches linked to the users
        if 'groups_id' in values:
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

    @api.multi
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
        if args is None:
            args = []
        user_ids = []
        if name and operator in ['=', 'ilike']:
            user_ids = self._search([('login', '=', name)] + args, limit=limit, access_rights_uid=name_get_uid)
        if not user_ids:
            user_ids = self._search([('name', operator, name)] + args, limit=limit, access_rights_uid=name_get_uid)
        return self.browse(user_ids).name_get()

    @api.multi
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

    @api.model
    @api.returns('ir.actions.act_window', lambda record: record.id)
    def action_get(self):
        return self.sudo().env.ref('base.action_res_users_my')

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

    @classmethod
    def _login(cls, db, login, password):
        if not password:
            raise AccessDenied()
        ip = request.httprequest.environ['REMOTE_ADDR'] if request else 'n/a'
        try:
            with cls.pool.cursor() as cr:
                self = api.Environment(cr, SUPERUSER_ID, {})[cls._name]
                with self._assert_can_auth():
                    user = self.search(self._get_login_domain(login))
                    if not user:
                        raise AccessDenied()
                    user = user.sudo(user.id)
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
        if uid == ADMINUSER_ID:
            # Successfully logged in as admin!
            # Attempt to guess the web base url...
            if user_agent_env and user_agent_env.get('base_location'):
                try:
                    with cls.pool.cursor() as cr:
                        base = user_agent_env['base_location']
                        ICP = api.Environment(cr, uid, {})['ir.config_parameter']
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

    @api.multi
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

    @api.multi
    def preference_save(self):
        return {
            'type': 'ir.actions.client',
            'tag': 'reload_context',
        }

    @api.multi
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
        return self.sudo(user=uid)._has_group(group_ext_id)

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
        assert group_ext_id and '.' in group_ext_id, "External ID must be fully qualified"
        module, ext_id = group_ext_id.split('.')
        self._cr.execute("""SELECT 1 FROM res_groups_users_rel WHERE uid=%s AND gid IN
                            (SELECT res_id FROM ir_model_data WHERE module=%s AND name=%s)""",
                         (self._uid, module, ext_id))
        return bool(self._cr.fetchone())
    # for a few places explicitly clearing the has_group cache
    has_group.clear_cache = _has_group.clear_cache

    @api.multi
    def _is_public(self):
        self.ensure_one()
        return self.has_group('base.group_public')

    @api.multi
    def _is_system(self):
        self.ensure_one()
        return self.has_group('base.group_system')

    @api.multi
    def _is_admin(self):
        self.ensure_one()
        return self._is_superuser() or self.has_group('base.group_erp_manager')

    @api.multi
    def _is_superuser(self):
        self.ensure_one()
        return self.id == SUPERUSER_ID

    @api.model
    def get_company_currency_id(self):
        return self.env.user.company_id.currency_id.id

    def _crypt_context(self):
        """ Passlib CryptContext instance used to encrypt and verify
        passwords. Can be overridden if technical, legal or political matters
        require different kdfs than the provided default.

        Requires a CryptContext as deprecation and upgrade notices are used
        internally
        """
        return DEFAULT_CRYPT_CONTEXT

    def _add_missing_default_values(self, vals):
        # Remove the default values of 'group_' and 'has_group' fields at the user creation if
        # 'groups_id' is provided in vals and if the fields value is not explicitely given.
        res = super(Users, self)._add_missing_default_values(vals)
        return {
            key: value for (key, value) in res.items()
            if 'groups_id' not in vals or key in vals or (not is_boolean_group(key) or not is_selection_groups(key))
        }

    def _get_group_selection(self, category_xml_id):
        """Returns the ordered selection for the given ir.module.category xmlid"""
        category = self.env.ref(category_xml_id, raise_if_not_found=False)
        selections = []
        if category:
            groups = self.env['res.groups'].search([('category_id', '=', category.id)])
            order = {group: len(group.trans_implied_ids & groups) for group in groups}
            groups = groups.sorted(key=order.get)
            selections = [(group.id, group.name) for group in groups]
        return selections

    @api.depends('groups_id')
    def _compute_groups_id(self):
        """Set the value for the group field (Selection of Boolean)
           according to the user's groups, defined by the field 'groups_id'.

           These methods should be used on fields defined like one the
           following cases:
           1. A boolean field with the compute/inverse method and an attribute
              group_xml_id.
           Example:
               has_group_discount_per_so_line = fields.Boolean(
                   "Discount on lines",
                   compute='_compute_groups_id', inverse='_inverse_groups_id',
                   group_xml_id='sale.group_discount_per_so_line')
           2. A selection field with the compute/inverse method, the selection
              got from '_get_group_selection' and an attribute
              'category_xml_id'
           Example:
               group_sales_team_user = fields.Selection(
                   selection=lambda self: self._get_group_selection('base.module_category_sales_management'),
                   string="Sales", compute='_compute_groups_id', inverse='_inverse_groups_id',
                   category_xml_id='base.module_category_sales_management')
           The fields will be set according to the groups defined in the 'groups_id'
           field, and the 'groups_id' field will be modified according to the
           modifications made on theses fields when saving the users's form.
        """
        computed_group_fields = [field for field in self._field_computed.keys() if field.compute == '_compute_groups_id']
        all_groups = self.env['res.groups'].search([])
        category_data = {}
        # Retrieve groups order for selection fields 
        for field in computed_group_fields:
            if getattr(field, 'category_xml_id', None):
                category = self.env.ref(getattr(field, 'category_xml_id'))
                category_groups = all_groups.filtered(lambda group: group.category_id == category)
                order = {group: len(group.trans_implied_ids & category_groups) for group in category_groups}
                category_data[field] = category_groups.sorted(key=order.get, reverse=True)
        # Set group fields values according to groups_id 
        for user in self:
            for field in computed_group_fields:
                # Checkbox group
                if getattr(field, 'group_xml_id', None):
                    group = self.env.ref(getattr(field, 'group_xml_id'))
                    user[field.name] = group in user.groups_id
                # Selection group
                elif getattr(field, 'category_xml_id', None):
                    # Take the highest level group the user belongs to
                    user_groups = [group for group in category_data[field] if group in user.groups_id]
                    user[field.name] = user_groups[0].id if user_groups else False
                else:
                    _logger.warning(_("No 'group_xml_id' or 'category_xml_id' is set on the computed field %s linked to the method _compute_groups_id") % (field.name))

    def _inverse_groups_id(self):
        """Update 'groups_id' according the group fields values in cache."""
        computed_group_fields = [field for field in self._field_computed.keys() if field.compute == '_compute_groups_id']
        all_groups = self.env['res.groups'].search([])
        for user in self:
            # we need to read all values in cache before any prefetch
            field_values = {field: user[field.name] for field in computed_group_fields if field.name in user._cache}
            groups_id_vals = []
            for field, value in field_values.items():
                # Checkbox group
                if getattr(field, 'group_xml_id', None):
                    selected_group = self.env.ref(getattr(field, 'group_xml_id'))
                    if value:
                        groups_id_vals.append((4, selected_group.id))
                    else:
                        groups_id_vals.append((3, selected_group.id))
                    for group in selected_group.trans_implied_ids:
                        groups_id_vals.append((4, group.id))
                # Selection group
                elif getattr(field, 'category_xml_id', None):
                    category = self.env.ref(getattr(field, 'category_xml_id'))
                    category_groups = [group for group in all_groups if group.category_id == category]
                    selected_group = [group for group in all_groups if group.id == value]
                    selected_group = selected_group and selected_group[0] or self.env['res.groups']
                    for group in category_groups:
                        if group in (selected_group.trans_implied_ids | selected_group):
                            groups_id_vals.append((4, group.id))
                        else:
                            groups_id_vals.append((3, group.id))
                else:
                    _logger.warning(_("No 'group_xml_id' or 'category_xml_id' is set on the computed field %s linked to the method _compute_groups_id") % (field.name))
            if groups_id_vals:
                user.write({'groups_id': groups_id_vals})

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
            _logger.warn(
                "Login attempt ignored for %s on %s: "
                "%d failures since last success, last failure at %s. "
                "You can configure the number of login failures before a "
                "user is put on cooldown as well as the duration in the "
                "System Parameters. Disable this feature by setting "
                "\"base.login_cooldown_after\" to 0.",
                source, self.env.cr.dbname, failures, previous)
            if ipaddress.ip_address(source).is_private:
                _logger.warn(
                    "The rate-limited IP address %s is classified as private "
                    "and *might* be a proxy. If your Odoo is behind a proxy, "
                    "it may be mis-configured. Check that you are running "
                    "Odoo in Proxy Mode and that the proxy is properly configured, see "
                    "https://www.odoo.com/documentation/11.0/setup/deploy.html#https for details.",
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
            return True

        delay = int(cfg.get_param('base.login_cooldown_duration', 60))
        return failures >= min_failures and (datetime.datetime.now() - previous) < datetime.timedelta(seconds=delay)

    def _register_hook(self):
        if hasattr(self, 'check_credentials'):
            _logger.warn("The check_credentials method of res.users has been renamed _check_credentials. One of your installed modules defines one, but it will not be called anymore.")

#
# Implied groups
#
# Extension of res.groups and res.users with a relation for "implied" or
# "inherited" groups.  Once a user belongs to a group, it automatically belongs
# to the implied groups (transitively).
#

class GroupsImplied(models.Model):
    _inherit = 'res.groups'

    implied_ids = fields.Many2many('res.groups', 'res_groups_implied_rel', 'gid', 'hid',
        string='Inherits', help='Users of this group automatically inherit those groups')
    trans_implied_ids = fields.Many2many('res.groups', string='Transitively inherits',
        compute='_compute_trans_implied')

    @api.depends('implied_ids.trans_implied_ids')
    def _compute_trans_implied(self):
        # Compute the transitive closure recursively. Note that the performance
        # is good, because the record cache behaves as a memo (the field is
        # never computed twice on a given group.)
        for g in self:
            g.trans_implied_ids = g.implied_ids | g.mapped('implied_ids.trans_implied_ids')

    @api.model_create_multi
    def create(self, vals_list):
        user_ids_list = [vals.pop('users', None) for vals in vals_list]
        groups = super(GroupsImplied, self).create(vals_list)
        for group, user_ids in pycompat.izip(groups, user_ids_list):
            if user_ids:
                # delegate addition of users to add implied groups
                group.write({'users': user_ids})
        return groups

    @api.multi
    def write(self, values):
        res = super(GroupsImplied, self).write(values)

        if values.get('users') or values.get('implied_ids'):
            # add all implied groups (to all users of each group)
            for group in self:
                vals = {'users': list(pycompat.izip(repeat(4), group.with_context(active_test=False).users.ids))}
                super(GroupsImplied, group.trans_implied_ids).write(vals)
        return res

class UsersImplied(models.Model):
    _inherit = 'res.users'

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if 'groups_id' in values:
                # complete 'groups_id' with implied groups
                user = self.new(values)
                gs = user.groups_id | user.groups_id.mapped('trans_implied_ids')
                values['groups_id'] = type(self).groups_id.convert_to_write(gs, user.groups_id)
        return super(UsersImplied, self).create(vals_list)

    @api.multi
    def write(self, values):
        res = super(UsersImplied, self).write(values)
        if values.get('groups_id'):
            # add implied groups for all users
            for user in self.with_context({}):
                gs = set(concat(g.trans_implied_ids for g in user.groups_id))
                vals = {'groups_id': [(4, g.id) for g in gs]}
                super(UsersImplied, user).write(vals)
        return res

#----------------------------------------------------------
# change password wizard
#----------------------------------------------------------

class ChangePasswordWizard(models.TransientModel):
    """ A wizard to manage the change of users' passwords. """
    _name = "change.password.wizard"
    _description = "Change Password Wizard"

    def _default_user_ids(self):
        user_ids = self._context.get('active_model') == 'res.users' and self._context.get('active_ids') or []
        return [
            (0, 0, {'user_id': user.id, 'user_login': user.login})
            for user in self.env['res.users'].browse(user_ids)
        ]

    user_ids = fields.One2many('change.password.user', 'wizard_id', string='Users', default=_default_user_ids)

    @api.multi
    def change_password_button(self):
        self.ensure_one()
        self.user_ids.change_password_button()
        if self.env.user in self.mapped('user_ids.user_id'):
            return {'type': 'ir.actions.client', 'tag': 'reload'}
        return {'type': 'ir.actions.act_window_close'}


class ChangePasswordUser(models.TransientModel):
    """ A model to configure users in the change password wizard. """
    _name = 'change.password.user'
    _description = 'Change Password Wizard User'

    wizard_id = fields.Many2one('change.password.wizard', string='Wizard', required=True, ondelete='cascade')
    user_id = fields.Many2one('res.users', string='User', required=True, ondelete='cascade')
    user_login = fields.Char(string='User Login', readonly=True)
    new_passwd = fields.Char(string='New Password', default='')

    @api.multi
    def change_password_button(self):
        for line in self:
            if not line.new_passwd:
                raise UserError(_("Before clicking on 'Change Password', you have to write a new password."))
            line.user_id.write({'password': line.new_passwd})
        # don't keep temporary passwords in the database longer than necessary
        self.write({'new_passwd': False})
