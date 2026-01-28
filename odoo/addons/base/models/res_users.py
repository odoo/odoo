# Part of Odoo. See LICENSE file for full copyright and licensing details.
from __future__ import annotations

import binascii
import contextlib
import collections
import datetime
import hmac
import ipaddress
import json
import logging
import os
import time
from functools import wraps
from hashlib import sha256
from itertools import chain
from markupsafe import Markup

import pytz
from lxml import etree
from passlib.context import CryptContext as _CryptContext

from odoo import api, fields, models, tools, _
from odoo.api import SUPERUSER_ID
from odoo.exceptions import AccessDenied, AccessError, UserError, ValidationError
from odoo.fields import Command, Domain
from odoo.http import request, DEFAULT_LANG
from odoo.tools import email_domain_extract, is_html_empty, frozendict, reset_cached_properties, str2bool, SQL


_logger = logging.getLogger(__name__)

class CryptContext:
    def __init__(self, *args, **kwargs):
        self.__obj__ = _CryptContext(*args, **kwargs)

    def copy(self):
        """
            The copy method must create a new instance of the
            ``CryptContext`` wrapper with the same configuration
            as the original (``__obj__``).

            There are no need to manage the case where kwargs are
            passed to the ``copy`` method.

            It is necessary to load the original ``CryptContext`` in
            the new instance of the original ``CryptContext`` with ``load``
            to get the same configuration.
        """
        other_wrapper = CryptContext(_autoload=False)
        other_wrapper.__obj__.load(self.__obj__)
        return other_wrapper

    @property
    def hash(self):
        return self.__obj__.hash

    @property
    def identify(self):
        return self.__obj__.identify

    @property
    def verify(self):
        return self.__obj__.verify

    @property
    def verify_and_update(self):
        return self.__obj__.verify_and_update

    def schemes(self):
        return self.__obj__.schemes()

    def update(self, **kwargs):
        if kwargs.get("schemes"):
            assert isinstance(kwargs["schemes"], str) or all(isinstance(s, str) for s in kwargs["schemes"])
        return self.__obj__.update(**kwargs)


MIN_ROUNDS = 600_000
concat = chain.from_iterable

def _jsonable(o):
    try: json.dumps(o)
    except TypeError: return False
    else: return True

def check_identity(fn):
    """ Wrapped method should be an *action method* (called from a button
    type=object), and requires extra security to be executed. This decorator
    checks if the identity (password) has been checked in the last 10mn, and
    pops up an identity check wizard if not.

    Prevents access outside of interactive contexts (aka with a request)
    """
    @wraps(fn)
    def wrapped(self, *args, **kwargs):
        if not request:
            raise UserError(_("This method can only be accessed over HTTP"))

        if request.session.get('identity-check-last', 0) > time.time() - 10 * 60:
            # update identity-check-last like github?
            return fn(self, *args, **kwargs)

        w = self.sudo().env['res.users.identitycheck'].create({
            'request': json.dumps([
                { # strip non-jsonable keys (e.g. mapped to recordsets)
                    k: v for k, v in self.env.context.items()
                    if _jsonable(v)
                },
                self._name,
                self.ids,
                fn.__name__,
                args,
                kwargs
            ])
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'res.users.identitycheck',
            'res_id': w.id,
            'name': _("Access Control"),
            'target': 'new',
            'views': [(False, 'form')],
            'context': {'dialog_size': 'medium'},
        }
    wrapped.__has_check_identity = True
    return wrapped

#----------------------------------------------------------
# Basic res.users
#----------------------------------------------------------


class ResUsersLog(models.Model):
    _name = 'res.users.log'
    _order = 'id desc'
    _description = 'Users Log'
    # Uses the magical fields `create_uid` and `create_date` for recording logins.
    # See `mail.presence` for more recent activity tracking purposes.

    create_uid = fields.Many2one('res.users', string='Created by', readonly=True, index=True)

    @api.autovacuum
    def _gc_user_logs(self):
        self.env.cr.execute("""
            DELETE FROM res_users_log log1 WHERE EXISTS (
                SELECT 1 FROM res_users_log log2
                WHERE log1.create_uid = log2.create_uid
                AND log1.create_date < log2.create_date
            )
        """)
        _logger.info("GC'd %d user log entries", self.env.cr.rowcount)


class ResUsers(models.Model):
    """ User class. A res.users record models an OpenERP user and is different
        from an employee.

        res.users class now inherits from res.partner. The partner model is
        used to store the data related to the partner: lang, name, address,
        avatar, ... The user model is now dedicated to technical data.
    """
    _name = 'res.users'
    _description = 'User'
    _inherits = {'res.partner': 'partner_id'}
    _order = 'name, login'
    _allow_sudo_commands = False

    def _check_company_domain(self, companies):
        if not companies:
            return Domain.TRUE
        company_ids = companies if isinstance(companies, str) else models.to_record_ids(companies)
        return Domain('company_ids', 'in', company_ids)

    @property
    def SELF_READABLE_FIELDS(self):
        """ The list of fields a user can read on their own user record.
        In order to add fields, please override this property on model extensions.
        """
        return [
            'signature', 'company_id', 'login', 'email', 'name', 'image_1920',
            'image_1024', 'image_512', 'image_256', 'image_128', 'lang', 'tz',
            'tz_offset', 'group_ids', 'partner_id', 'write_date', 'action_id',
            'avatar_1920', 'avatar_1024', 'avatar_512', 'avatar_256', 'avatar_128',
            'share', 'device_ids', 'api_key_ids', 'phone', 'display_name',
        ]

    @property
    def SELF_WRITEABLE_FIELDS(self):
        """ The list of fields a user can write on their own user record.
        In order to add fields, please override this property on model extensions.
        """
        return ['signature', 'action_id', 'company_id', 'email', 'name', 'image_1920', 'lang', 'tz', 'api_key_ids', 'phone']

    @api.model
    @tools.ormcache(cache='stable')
    def _self_accessible_fields(self) -> tuple[frozenset[str], frozenset[str]]:
        """Readable and writable fields by portal users."""
        readable = frozenset(self.SELF_READABLE_FIELDS)
        writeable = frozenset(self.SELF_WRITEABLE_FIELDS)
        return readable, writeable

    def _default_groups(self):
        """Default groups for employees

        All the groups of the Default User Group
        """
        groups = self.env.ref('base.group_user')
        default_group = self.env.ref('base.default_user_group', raise_if_not_found=False)
        if default_group:
            groups += default_group.implied_ids
        return groups

    partner_id = fields.Many2one('res.partner', required=True, ondelete='restrict', bypass_search_access=True, index=True,
        string='Related Partner', help='Partner-related data of the user')
    login = fields.Char(required=True, help="Used to log into the system")
    password = fields.Char(
        compute='_compute_password', inverse='_set_password', copy=False,
        help="Keep empty if you don't want the user to be able to connect on the system.")
    new_password = fields.Char(string='Set Password',
        compute='_compute_password', inverse='_set_new_password',
        help="Specify a value only when creating a user or if you're "\
             "changing the user's password, otherwise leave empty. After "\
             "a change of password, the user has to login again.")
    api_key_ids = fields.One2many('res.users.apikeys', 'user_id', string="API Keys")
    signature = fields.Html(string="Email Signature", compute='_compute_signature', readonly=False, store=True)
    active = fields.Boolean(default=True)
    active_partner = fields.Boolean(related='partner_id.active', readonly=True, string="Partner is Active")
    action_id = fields.Many2one('ir.actions.actions', string='Home Action',
        help="If specified, this action will be opened at log on for this user, in addition to the standard menu.")
    log_ids = fields.One2many('res.users.log', 'create_uid', string='User log entries')
    device_ids = fields.One2many('res.device', 'user_id', string='User devices')
    login_date = fields.Datetime(related='log_ids.create_date', string='Latest Login', readonly=False)
    share = fields.Boolean(compute='_compute_share', compute_sudo=True, string='Share User', store=True,
         help="External user with limited access, created only for the purpose of sharing data.")
    companies_count = fields.Integer(compute='_compute_companies_count', string="Number of Companies")
    tz_offset = fields.Char(compute='_compute_tz_offset', string='Timezone offset')
    res_users_settings_ids = fields.One2many('res.users.settings', 'user_id')
    # Provide a target for relateds that is not a x2Many field.
    res_users_settings_id = fields.Many2one('res.users.settings', string="Settings", compute='_compute_res_users_settings_id', search='_search_res_users_settings_id')

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
    email_domain_placeholder = fields.Char(compute="_compute_email_domain_placeholder")
    phone = fields.Char(related='partner_id.phone', inherited=True, readonly=False)

    group_ids = fields.Many2many('res.groups', 'res_groups_users_rel', 'uid', 'gid', string='Groups', default=lambda s: s._default_groups(), help="Groups explicitly assigned to the user")
    all_group_ids = fields.Many2many('res.groups', string="Groups and implied groups",
        compute='_compute_all_group_ids', compute_sudo=True, search='_search_all_group_ids')

    accesses_count = fields.Integer('# Access Rights', help='Number of access rights that apply to the current user',
                                    compute='_compute_accesses_count', compute_sudo=True)
    rules_count = fields.Integer('# Record Rules', help='Number of record rules that apply to the current user',
                                 compute='_compute_accesses_count', compute_sudo=True)
    groups_count = fields.Integer('# Groups', help='Number of groups that apply to the current user',
                                  compute='_compute_accesses_count', compute_sudo=True)

    def _default_view_group_hierarchy(self):
        return self.env['res.groups']._get_view_group_hierarchy()

    view_group_hierarchy = fields.Json(string='Technical field for user group setting', store=False, copy=False, default=_default_view_group_hierarchy)
    role = fields.Selection([('group_user', 'User'), ('group_system', 'Administrator')], compute='_compute_role', readonly=False, string="Role")

    _login_key = models.Constraint("UNIQUE (login)",
        'You can not have two users with the same login!')

    def init(self):
        cr = self.env.cr

        # allow setting plaintext passwords via SQL and have them
        # automatically encrypted at startup: look for passwords which don't
        # match the "extended" MCF and pass those through passlib.
        # Alternative: iterate on *all* passwords and use CryptContext.identify
        cr.execute(r"""
        SELECT id, password FROM res_users
        WHERE password IS NOT NULL
          AND password !~ '^\$[^$]+\$[^$]+\$.'
        """)
        if self.env.cr.rowcount:
            ResUsers = self.sudo()
            for uid, pw in cr.fetchall():
                ResUsers.browse(uid).password = pw

    def _set_password(self):
        ctx = self._crypt_context()
        for user in self:
            self._set_encrypted_password(user.id, ctx.hash(user.password))

    def _set_encrypted_password(self, uid, pw):
        assert self._crypt_context().identify(pw) != 'plaintext'

        self.env.cr.execute(
            'UPDATE res_users SET password=%s WHERE id=%s',
            (pw, uid)
        )
        self.browse(uid).invalidate_recordset(['password'])

    def _rpc_api_keys_only(self):
        """ To be overridden if RPC access needs to be restricted to API keys, e.g. for 2FA """
        return False

    def _check_credentials(self, credential, env):
        """ Validates the current user's password.

        Override this method to plug additional authentication methods.

        Overrides should:

        * call ``super`` to delegate to parents for credentials-checking
        * catch :class:`~odoo.exceptions.AccessDenied` and perform their
          own checking
        * (re)raise :class:`~odoo.exceptions.AccessDenied` if the
          credentials are still invalid according to their own
          validation method
        * return the ``auth_info``

        When trying to check for credentials validity, call
        :meth:`_check_credentials` instead.

        Credentials are considered to be untrusted user input, for more
        information please check :meth:`authenticate`

        :returns: ``auth_info`` dictionary containing:

          - uid: the uid of the authenticated user
          - auth_method: which method was used during authentication
          - mfa: whether mfa should be skipped or not, possible values:

            - enforce: enforce mfa no matter what (not yet implemented)
            - default: delegate to auth_totp
            - skip: skip mfa no matter what

          Examples:

          - ``{ 'uid': 20, 'auth_method': 'password',      'mfa': 'default' }``
          - ``{ 'uid': 17, 'auth_method': 'impersonation', 'mfa': 'enforce' }``
          - ``{ 'uid': 32, 'auth_method': 'webauthn',      'mfa': 'skip'    }``
        :rtype: dict
        """
        if not (credential['type'] == 'password' and credential.get('password')):
            raise AccessDenied()

        env = env or {}
        interactive = env.get('interactive', True)

        if interactive or not self.env.user._rpc_api_keys_only():
            if 'interactive' not in env:
                _logger.warning(
                    "_check_credentials without 'interactive' env key, assuming interactive login. \
                    Check calls and overrides to ensure the 'interactive' key is properly set in \
                    all _check_credentials environments"
                )

            self.env.cr.execute(
                "SELECT COALESCE(password, '') FROM res_users WHERE id=%s",
                [self.env.user.id]
            )
            [hashed] = self.env.cr.fetchone()
            valid, replacement = self._crypt_context()\
                .verify_and_update(credential['password'], hashed)
            if replacement is not None:
                self._set_encrypted_password(self.env.user.id, replacement)
                if request and self == self.env.user:
                    self.env.flush_all()
                    self.env.registry.clear_cache()
                    # update session token so the user does not get logged out
                    new_token = self.env.user._compute_session_token(request.session.sid)
                    request.session.session_token = new_token

            if valid:
                return {
                    'uid': self.env.user.id,
                    'auth_method': 'password',
                    'mfa': 'default',
                }

        if not interactive:
            # 'rpc' scope does not really exist, we basically require a global key (scope NULL)
            if self.env['res.users.apikeys']._check_credentials(scope='rpc', key=credential['password']) == self.env.uid:
                return {
                    'uid': self.env.user.id,
                    'auth_method': 'apikey',
                    'mfa': 'default',
                }

            if self.env.user._rpc_api_keys_only():
                _logger.info(
                    "Invalid API key or password-based authentication attempted for a non-interactive (API) "
                    "context that requires API key authentication only."
                )

        raise AccessDenied()

    @api.depends_context('uid')
    def _compute_email_domain_placeholder(self):
        domain = email_domain_extract(self.env.user.email)
        self.email_domain_placeholder = _('e.g. %(placeholder)s', placeholder=f'email@{domain}') if domain else _('Email')

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

    @api.depends('group_ids')
    def _compute_role(self):
        for user in self:
            user.role = (
                'group_system' if user.has_group('base.group_system') else
                'group_user' if user.has_group('base.group_user') else
                False
            )

    @api.onchange('role')
    def _onchange_role(self):
        group_admin = self.env['res.groups'].new(origin=self.env.ref('base.group_system'))
        group_user = self.env['res.groups'].new(origin=self.env.ref('base.group_user'))
        for user in self:
            if user.role and user.has_group('base.group_user'):
                groups = user.group_ids - (group_admin + group_user)
                user.group_ids = groups + (group_admin if user.role == 'group_system' else group_user)

    @api.depends('group_ids.all_implied_ids')
    def _compute_all_group_ids(self):
        for user in self:
            user.all_group_ids = user.group_ids.all_implied_ids

    def _search_all_group_ids(self, operator, value):
        return [('group_ids.all_implied_ids', operator, value)]

    @api.depends('name')
    def _compute_signature(self):
        for user in self.filtered(lambda user: user.name and is_html_empty(user.signature)):
            user.signature = Markup('<div>%s</div>') % user['name']

    @api.depends('all_group_ids')
    def _compute_share(self):
        user_group_id = self.env['ir.model.data']._xmlid_to_res_id('base.group_user')
        internal_users = self.filtered_domain([('all_group_ids', 'in', [user_group_id])])
        internal_users.share = False
        (self - internal_users).share = True

    @api.depends('company_id')
    def _compute_companies_count(self):
        self.companies_count = self.env['res.company'].sudo().search_count([])

    @api.depends('tz')
    def _compute_tz_offset(self):
        for user in self:
            user.tz_offset = datetime.datetime.now(pytz.timezone(user.tz or 'GMT')).strftime('%z')

    @api.depends('all_group_ids')
    def _compute_accesses_count(self):
        for user in self:
            groups = user.all_group_ids
            user.accesses_count = len(groups.model_access)
            user.rules_count = len(groups.rule_groups)
            user.groups_count = len(groups)

    @api.depends('res_users_settings_ids')
    def _compute_res_users_settings_id(self):
        for user in self:
            user.res_users_settings_id = user.res_users_settings_ids and user.res_users_settings_ids[0]

    @api.model
    def _search_res_users_settings_id(self, operator, operand):
        return Domain('res_users_settings_ids', operator, operand)

    @api.onchange('login')
    def on_change_login(self):
        if self.login and tools.single_email_re.match(self.login):
            self.email = self.login

    @api.onchange('parent_id')
    def onchange_parent_id(self):
        return self.partner_id.onchange_parent_id()

    @api.constrains('company_id', 'company_ids', 'active')
    def _check_user_company(self):
        for user in self.filtered(lambda u: u.active):
            if user.company_id not in user.company_ids:
                raise ValidationError(
                    _('Company %(company_name)s is not in the allowed companies for user %(user_name)s (%(company_allowed)s).',
                      company_name=user.company_id.name,
                      user_name=user.name,
                      company_allowed=', '.join(user.mapped('company_ids.name')))
                )

    @api.constrains('action_id')
    def _check_action_id(self):
        action_open_website = self.env.ref('base.action_open_website', raise_if_not_found=False)
        if action_open_website and any(user.action_id.id == action_open_website.id for user in self):
            raise ValidationError(_('The "App Switcher" action cannot be selected as home action.'))
        # We use sudo() because  "Access rights" admins can't read action models
        for user in self.sudo():
            if user.action_id.type == "ir.actions.client":
                # Prevent using reload actions.
                action = self.env["ir.actions.client"].browse(user.action_id.id)  # magic
                if action.tag == "reload":
                    raise ValidationError(_('The "%s" action cannot be selected as home action.', action.name))

            elif user.action_id.type == "ir.actions.act_window":
                # Restrict actions that include 'active_id' in their context.
                action = self.env["ir.actions.act_window"].browse(user.action_id.id)  # magic
                if not action.context:
                    continue
                if "active_id" in action.context:
                    raise ValidationError(
                        _('The action "%s" cannot be set as the home action because it requires a record to be selected beforehand.', action.name)
                    )

    @api.constrains('group_ids')
    def _check_disjoint_groups(self):
        """We check that no users are both portal and users (same with public).
           This could typically happen because of implied groups.
        """
        user_type_groups = self.env['res.groups']._get_user_type_groups()
        for user in self:
            disjoint_groups = user.all_group_ids & user_type_groups
            if len(disjoint_groups) > 1:
                raise ValidationError(_(
                    "User %(user)s cannot be at the same time in exclusive groups %(groups)s.",
                    user=repr(user.name),
                    groups=", ".join(repr(g.display_name) for g in disjoint_groups),
                ))

    @api.constrains('group_ids')
    def _check_at_least_one_administrator(self):
        if not self.env.registry._init_modules:
            return  # ignore the constraint when updating the module 'base'
        if not self.env.ref('base.group_system').user_ids:
            raise ValidationError(_("You must have at least an administrator user."))

    def onchange(self, values, field_names, fields_spec):
        # Hacky fix to access fields in `SELF_READABLE_FIELDS` in the onchange logic.
        # Put field values in the cache.
        if self == self.env.user:
            [self.sudo()[field_name] for field_name in self._self_accessible_fields()[0]]
        return super().onchange(values, field_names, fields_spec)

    def read(self, fields=None, load='_classic_read'):
        readable, _ = self._self_accessible_fields()
        if fields and self == self.env.user and all(key in readable or key.startswith('context_') for key in fields):
            # safe fields only, so we read as super-user to bypass access rights
            self = self.sudo()
        return super().read(fields=fields, load=load)

    def _has_field_access(self, field, operation):
        return super()._has_field_access(field, operation) or (
            operation == 'read'
            and self._origin == self.env.user
            and field.name in self._self_accessible_fields()[0]
        )

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        setting_vals = []
        for user in users:
            if not user.res_users_settings_ids and user._is_internal():
                setting_vals.append({'user_id': user.id})
            # if partner is global we keep it that way
            if user.partner_id.company_id:
                user.partner_id.company_id = user.company_id
            user.partner_id.active = user.active
            # Generate employee initals as avatar for internal users without image
            if not user.image_1920 and not user.share and user.name:
                user.image_1920 = user.partner_id._avatar_generate_svg()
        if setting_vals:
            self.env['res.users.settings'].sudo().create(setting_vals)
        return users

    def write(self, vals):
        if vals.get('active') and SUPERUSER_ID in self._ids:
            raise UserError(_("You cannot activate the superuser."))
        if vals.get('active') == False and self.env.uid in self._ids:  # noqa: E712
            raise UserError(_("You cannot deactivate the user you're currently logged in as."))

        if vals.get('active'):
            # unarchive partners before unarchiving the users
            self.partner_id.action_unarchive()
        if self == self.env.user:
            writeable = self._self_accessible_fields()[1]
            for key in list(vals):
                if key not in writeable:
                    break
            else:
                if 'company_id' in vals:
                    if vals['company_id'] not in self.env.user.company_ids.ids:
                        del vals['company_id']
                # safe fields only, so we write as super-user to bypass access rights
                self = self.sudo()

        res = super().write(vals)

        if 'company_id' in vals:
            for user in self:
                # if partner is global we keep it that way
                if user.partner_id.company_id and user.partner_id.company_id.id != vals['company_id']:
                    user.partner_id.write({'company_id': user.company_id.id})

        if 'company_id' in vals or 'company_ids' in vals:
            # Reset lazy properties `company` & `companies` on all envs,
            # This is unlikely in a business code to change the company of a user and then do business stuff
            # but in case it happens this is handled.
            # e.g. `account_test_savepoint.py` `setup_company_data`, triggered by `test_account_invoice_report.py`
            for env in list(self.env.transaction.envs):
                if env.user in self:
                    reset_cached_properties(env)

        if 'group_ids' in vals and self.ids:
            # clear caches linked to the users
            self.env['ir.model.access'].call_cache_clearing_methods()

        # per-method / per-model caches have been removed so the various
        # clear_cache/clear_caches methods pretty much just end up calling
        # Registry.clear_cache
        invalidation_fields = self._get_invalidation_fields()
        if invalidation_fields & vals.keys():
            self.env.registry.clear_cache()

        return res

    @api.ondelete(at_uninstall=True)
    def _unlink_except_master_data(self):
        portal_user_template = self.env.ref('base.template_portal_user_id', False)
        public_user = self.env.ref('base.public_user', False)
        if SUPERUSER_ID in self.ids:
            raise UserError(_('You can not remove the admin user as it is used internally for resources created by Odoo (updates, module installation, ...)'))
        user_admin = self.env.ref('base.user_admin', raise_if_not_found=False)
        if user_admin and user_admin in self:
            raise UserError(_('You cannot delete the admin user because it is utilized in various places (such as security configurations,...). Instead, archive it.'))
        self.env.registry.clear_cache()
        if portal_user_template and portal_user_template in self:
            raise UserError(_('Deleting the template users is not allowed. Deleting this profile will compromise critical functionalities.'))
        if public_user and public_user in self:
            raise UserError(_("Deleting the public user is not allowed. Deleting this profile will compromise critical functionalities."))

    @api.model
    def name_search(self, name='', domain=None, operator='ilike', limit=100):
        domain = Domain(domain or Domain.TRUE)
        # first search only by login, then the normal search
        if (
            name and not operator in Domain.NEGATIVE_OPERATORS
            and (user := self.search_fetch(Domain('login', '=', name) & domain, ['display_name']))
        ):
            return [(user.id, user.display_name)]
        return super().name_search(name, domain, operator, limit)

    @api.model
    def _search_display_name(self, operator, value):
        domain = super()._search_display_name(operator, value)
        if operator in ('in', 'ilike') and value:
            name_domain = [('login', 'in', [value] if isinstance(value, str) else value)]
            # avoid searching both by login and name because they reside in two different tables
            # doing so prevents from using indexes and introduces a performance issue
            if users := self.search(name_domain):
                domain = [('id', 'in', users.ids)]
        return domain

    def copy_data(self, default=None):
        default = dict(default or {})
        vals_list = super().copy_data(default=default)
        for user, vals in zip(self, vals_list):
            if ('name' not in default) and ('partner_id' not in default):
                vals['name'] = _("%s (copy)", user.name)
            if 'login' not in default:
                vals['login'] = _("%s (copy)", user.login)
        return vals_list

    @api.model
    @tools.ormcache('self.env.uid')
    def context_get(self):
        # use read() to not read other fields: this must work while modifying
        # the schema of models res.users or res.partner
        try:
            context = self.env.user.read(['lang', 'tz'], load=False)[0]
        except IndexError:
            # user not found, no context information
            return frozendict()
        context.pop('id')

        # ensure lang is set and available
        # context > request > company > english > any lang installed
        langs = [code for code, _ in self.env['res.lang'].get_installed()]
        lang = context.get('lang')
        if lang not in langs:
            lang = request.best_lang if request else None
            if lang not in langs:
                lang = self.env.user.with_context(prefetch_fields=False).company_id.partner_id.lang
                if lang not in langs:
                    lang = DEFAULT_LANG
                    if lang not in langs:
                        lang = langs[0] if langs else DEFAULT_LANG
        context['lang'] = lang

        # ensure uid is set
        context['uid'] = self.env.uid

        return frozendict(context)

    @tools.ormcache('self.id')
    def _get_company_ids(self):
        # use search() instead of `self.company_ids` to avoid extra query for `active_test`
        domain = [('active', '=', True), ('user_ids', 'in', self.id)]
        return self.env['res.company'].search(domain)._ids

    @api.model
    def action_get(self):
        return self.sudo().env.ref('base.action_res_users_my').read()[0]

    @api.model
    def _get_invalidation_fields(self):
        return {
            'group_ids', 'active', 'lang', 'tz', 'company_id', 'company_ids',
            *self._get_session_token_fields()
        }

    @api.model
    def _update_last_login(self):
        # only create new records to avoid any side-effect on concurrent transactions
        # extra records will be deleted by the periodical garbage collection
        self.env['res.users.log'].sudo().create({}) # populated by defaults

    @api.model
    def _get_login_domain(self, login):
        return Domain('login', '=', login)

    @api.model
    def _get_email_domain(self, email):
        return Domain('email', '=', email)

    @api.model
    def _get_login_order(self):
        return self._order

    def _login(self, credential, user_agent_env):
        login = credential['login']
        ip = request.httprequest.environ['REMOTE_ADDR'] if request else 'n/a'
        try:
            with self._assert_can_auth(user=login):
                user = self.sudo().search(self._get_login_domain(login), order=self._get_login_order(), limit=1)
                if not user:
                    # ruff: noqa: TRY301
                    raise AccessDenied()
                user = user.with_user(user).sudo()
                auth_info = user._check_credentials(credential, user_agent_env)
                tz = request.cookies.get('tz') if request else None
                if tz in pytz.all_timezones and (not user.tz or not user.login_date):
                    # first login or missing tz -> set tz to browser tz
                    user.tz = tz
                user._update_last_login()
        except AccessDenied:
            _logger.info("Login failed for login:%s from %s", login, ip)
            raise

        _logger.info("Login successful for login:%s from %s", login, ip)

        return auth_info

    def authenticate(self, credential, user_agent_env):
        """Verifies and returns the user ID corresponding to the given
        ``credential``, or False if there was no matching user.

        :param dict credential: a dictionary where the `type` key defines the authentication method and
            additional keys are passed as required per authentication method.
            For example:
            - { 'type': 'password', 'login': 'username', 'password': '123456' }
            - { 'type': 'webauthn', 'webauthn_response': '{json data}' }
        :param dict user_agent_env: environment dictionary describing any
            relevant environment attributes
        :return: auth_info
        :rtype: dict
        """
        auth_info = self._login(credential, user_agent_env=user_agent_env)
        if user_agent_env and user_agent_env.get('base_location'):
            env = self.env(user=auth_info['uid'])
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
        return auth_info

    @api.model
    @tools.ormcache('uid', 'passwd')
    def _check_uid_passwd(self, uid, passwd):
        """Verifies that the given (uid, password) is authorized and
           raise an exception if it is not."""
        if not passwd:
            # empty passwords disallowed for obvious security reasons
            raise AccessDenied()

        with self._assert_can_auth(user=uid):
            user = self.with_user(uid).env.user
            if not user.active:
                raise AccessDenied()
            credential = {'login': user.login, 'password': passwd, 'type': 'password'}
            user._check_credentials(credential, {'interactive': False})

    def _get_session_token_fields(self):
        return {'id', 'login', 'password', 'active'}

    def _get_session_token_query_params(self):
        database_secret = SQL("SELECT value FROM ir_config_parameter WHERE key='database.secret'")
        fields = SQL(", ").join(
            SQL.identifier(self._table, fname)
            for fname in sorted(self._get_session_token_fields())
            # To handle `auth_passkey_key_ids`,
            # which we want in the `_get_session_token_fields` list for the cache invalidation mechanism
            # but which we do not want here as it isn't an actual column in the res_users table.
            # Instead, the left join to that table is done with an override of `_get_session_token_query_params`.
            if not self._fields[fname].relational
        )
        return {
            "select": SQL("(%s) as database_secret, %s", database_secret, fields),
            "from": SQL("res_users"),
            "joins": SQL(""),
            "where": SQL("res_users.id = %s", self.id),
            "group_by": SQL("res_users.id"),
        }

    @tools.ormcache('sid')
    def _compute_session_token(self, sid):
        """ Compute a session token given a session id and a user id """
        # retrieve the fields used to generate the session token
        field_values = self._session_token_get_values()
        return self._session_token_hash_compute(sid, field_values)

    def _session_token_get_values(self):
        self.env.cr.execute(SQL(
            "SELECT %(select)s FROM %(from)s %(joins)s WHERE %(where)s GROUP BY %(group_by)s",
            **self._get_session_token_query_params(),
        ))
        if self.env.cr.rowcount != 1:
            self.env.registry.clear_cache()
            return False
        data_fields = self.env.cr.fetchone()
        # create tuple with column name and value, allowing for overrides to manipulate the values
        cr_description = self.env.cr.description
        return tuple((column.name, data_fields[index]) for index, column in enumerate(cr_description))

    def _session_token_hash_compute(self, sid, field_values):
        if not field_values:
            return False
        # Generate hmac key using the column name and its value, only if the value is not None
        # To avoid invalidating sessions when installing a new feature modifying the session token computation
        # while not still being used.
        key_tuple = tuple((k, v) for k, v in field_values if v is not None)
        # encode the key tuple to a bytestring
        key = str(key_tuple).encode()
        # hmac the session id
        data = sid.encode()
        h = hmac.new(key, data, sha256)
        # return the session token with a prefix version
        return h.hexdigest()

    def _legacy_session_token_hash_compute(self, sid):
        field_values = self._session_token_get_values()
        if not field_values:
            return False
        # generate hmac key
        key = ('%s' % (tuple(f[1] for f in field_values),)).encode()
        # hmac the session id
        data = sid.encode()
        h = hmac.new(key, data, sha256)
        # keep in the cache the token
        return h.hexdigest()

    @api.model
    def change_password(self, old_passwd, new_passwd):
        """Change current user password. Old password must be provided explicitly
        to prevent hijacking an existing user session, or for cases where the cleartext
        password is not used to authenticate requests.

        :return: True
        :raise: odoo.exceptions.AccessDenied when old password is wrong
        :raise: odoo.exceptions.UserError when new password is not set or empty
        """
        if not old_passwd:
            raise AccessDenied()

        # alternatively: use identitycheck wizard?
        credential = {'login': self.env.user.login, 'password': old_passwd, 'type': 'password'}
        self._check_credentials(credential, {'interactive': True})

        # use self.env.user here, because it has uid=SUPERUSER_ID
        self.env.user._change_password(new_passwd)
        return True

    def _change_password(self, new_passwd):
        new_passwd = new_passwd.strip()
        if not new_passwd:
            raise UserError(_("Setting empty passwords is not allowed for security reasons!"))

        ip = request.httprequest.environ['REMOTE_ADDR'] if request else 'n/a'
        _logger.info(
            "Password change for %r (#%d) by %r (#%d) from %s",
             self.login, self.id,
             self.env.user.login, self.env.user.id,
             ip
        )

        self.password = new_passwd

    def _deactivate_portal_user(self, **post):
        """Try to remove the current portal user.

        This is used to give the opportunity to portal users to de-activate their accounts.
        Indeed, as the portal users can easily create accounts, they will sometimes wish
        it removed because they don't use this Odoo portal anymore.

        Before this feature, they would have to contact the website or the support to get
        their account removed, which could be tedious.
        """
        non_portal_users = self.filtered(lambda user: not user.share)
        if non_portal_users:
            raise AccessDenied(_(
                'Only the portal users can delete their accounts. '
                'The user(s) %s can not be deleted.',
                ', '.join(non_portal_users.mapped('name')),
            ))

        ip = request.httprequest.environ['REMOTE_ADDR'] if request else 'n/a'

        res_users_deletion_values = []

        for user in self:
            _logger.info(
                'Account deletion asked for "%s" (#%i) from %s. '
                'Archive the user and remove login information.',
                user.login, user.id, ip,
            )

            user.write({
                'login': f'__deleted_user_{user.id}_{time.time()}',
                'password': '',
            })
            user.api_key_ids._remove()

            res_users_deletion_values.append({
                'user_id': user.id,
                'state': 'todo',
            })

        # Here we try to archive the user / partner, and then add the user in a deletion
        # queue, to remove it from the database. As the deletion might fail (if the
        # partner is related to an invoice e.g.) it's important to archive it here.
        try:
            # A user can not self-deactivate
            self.with_user(SUPERUSER_ID).action_archive()
        except Exception:
            pass
        try:
            self.partner_id.action_archive()
        except Exception:
            pass
        # Add users in the deletion queue
        self.env['res.users.deletion'].create(res_users_deletion_values)

    def preference_save(self):
        return {
            'type': 'ir.actions.client',
            'tag': 'reload_context',
        }

    def action_change_password_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_model': 'change.password.wizard',
            'view_mode': 'form',
        }

    @check_identity
    def preference_change_password(self):
        return {
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_model': 'change.password.own',
            'view_mode': 'form',
        }

    @check_identity
    def api_key_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'res.users.apikeys.description',
            'name': 'New API Key',
            'target': 'new',
            'views': [(False, 'form')],
        }

    @check_identity
    def action_revoke_all_devices(self):
        # self.env.user is sudo by default
        # Need sudo to bypass access error for removing the devices of portal user
        return (self.env.user if self.id == self.env.uid else self)._action_revoke_all_devices()

    def _action_revoke_all_devices(self):
        devices = self.env["res.device"].search([("user_id", "=", self.id)])
        devices.filtered(lambda d: not d.is_current)._revoke()
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    @api.readonly
    def has_groups(self, group_spec: str) -> bool:
        """ Return whether user ``self`` satisfies the given group restrictions
        ``group_spec``, i.e., whether it is member of at least one of the groups,
        and is not a member of any of the groups preceded by ``!``.

        Note that the group ``"base.group_no_one"`` is only effective in debug
        mode, just like method :meth:`~.has_group` does.

        :param str group_spec: comma-separated list of fully-qualified group
            external IDs, optionally preceded by ``!``.
            Example:``"base.group_user,base.group_portal,!base.group_system"``.
        """
        if group_spec == '.':
            return False

        positives = []
        negatives = []
        for group_ext_id in group_spec.split(','):
            group_ext_id = group_ext_id.strip()
            if group_ext_id.startswith('!'):
                negatives.append(group_ext_id[1:])
            else:
                positives.append(group_ext_id)

        # for the sake of performance, check negatives first
        if any(self.has_group(ext_id) for ext_id in negatives):
            return False
        if any(self.has_group(ext_id) for ext_id in positives):
            return True
        return not positives

    @api.readonly
    def has_group(self, group_ext_id: str) -> bool:
        """ Return whether user ``self`` belongs to the given group (given by its
        fully-qualified external ID).

        Note that the group ``"base.group_no_one"`` is only effective in debug
        mode: the method returns ``True`` if the user belongs to the group and
        the current request is in debug mode.
        """
        self.ensure_one()
        if not (self.env.su or self == self.env.user or self.env.user._has_group('base.group_user')):
            # this prevents RPC calls from non-internal users to retrieve
            # information about other users
            raise AccessError(_("You can ony call user.has_group() with your current user."))

        result = self._has_group(group_ext_id)
        if group_ext_id == 'base.group_no_one':
            result = result and bool(request and request.session.debug)
        return result

    def _has_group(self, group_ext_id: str) -> bool:
        """ Return whether user ``self`` belongs to the given group.

        :param str group_ext_id: external ID (XML ID) of the group.
           Must be provided in fully-qualified form (``module.ext_id``), as there
           is no implicit module to use..
        :return: True if user ``self`` is a member of the group with the
           given external ID (XML ID), else False.
        """
        group_id = self.env['res.groups']._get_group_definitions().get_id(group_ext_id)
        # for new record don't fill the ormcache
        return group_id in (self._get_group_ids() if self.id else self.all_group_ids._origin._ids)

    @tools.ormcache('self.id')
    def _get_group_ids(self):
        """ Return ``self``'s group ids (as a tuple)."""
        self.ensure_one()
        # `with_context({})` because this method is decorated with `@ormcache('self._ids')`,
        # it cannot depend on the context (e.g. `active_test`, `lang`, ...)
        return self.with_context({}).all_group_ids._ids

    def _action_show(self):
        """If self is a singleton, directly access the form view. If it is a recordset, open a list view"""
        view_id = self.env.ref('base.view_users_form').id
        action = {
            'type': 'ir.actions.act_window',
            'res_model': 'res.users',
            'context': {'create': False},
        }
        if len(self) > 1:
            action.update({
                'name': _('Users'),
                'view_mode': 'list,form',
                'views': [[None, 'list'], [view_id, 'form']],
                'domain': [('id', 'in', self.ids)],
            })
        else:
            action.update({
                'view_mode': 'form',
                'views': [[view_id, 'form']],
                'res_id': self.id,
            })
        return action

    def action_show_groups(self):
        self.ensure_one()
        return {
            'name': _('Groups'),
            'view_mode': 'list,form',
            'res_model': 'res.groups',
            'type': 'ir.actions.act_window',
            'context': {'create': False, 'delete': False},
            'domain': [('id', 'in', self.all_group_ids.ids)],
            'target': 'current',
        }

    def action_show_accesses(self):
        self.ensure_one()
        return {
            'name': _('Access Rights'),
            'view_mode': 'list,form',
            'res_model': 'ir.model.access',
            'type': 'ir.actions.act_window',
            'context': {'create': False, 'delete': False},
            'domain': [('id', 'in', self.all_group_ids.model_access.ids)],
            'target': 'current',
        }

    def action_show_rules(self):
        self.ensure_one()
        return {
            'name': _('Record Rules'),
            'view_mode': 'list,form',
            'res_model': 'ir.rule',
            'type': 'ir.actions.act_window',
            'context': {'create': False, 'delete': False},
            'domain': [('id', 'in', self.all_group_ids.rule_groups.ids)],
            'target': 'current',
        }

    def _is_internal(self):
        self.ensure_one()
        return self.sudo().has_group('base.group_user')

    def _is_portal(self):
        self.ensure_one()
        return self.sudo().has_group('base.group_portal')

    def _is_public(self):
        self.ensure_one()
        return self.sudo().has_group('base.group_public')

    def _is_system(self):
        self.ensure_one()
        return self.sudo().has_group('base.group_system')

    def _is_admin(self):
        self.ensure_one()
        return self._is_superuser() or self.sudo().has_group('base.group_erp_manager')

    def _is_superuser(self):
        self.ensure_one()
        return self.id == SUPERUSER_ID

    @api.model
    def get_company_currency_id(self):
        return self.env.company.currency_id.id

    @tools.ormcache(cache='stable')
    def _crypt_context(self):
        """ Passlib CryptContext instance used to encrypt and verify
        passwords. Can be overridden if technical, legal or political matters
        require different kdfs than the provided default.

        The work factor of the default KDF can be configured using the
        ``password.hashing.rounds`` ICP.
        """
        cfg = self.env['ir.config_parameter'].sudo()
        return CryptContext(
            # kdf which can be verified by the context. The default encryption
            # kdf is the first of the list
            ['pbkdf2_sha512', 'plaintext'],
            # deprecated algorithms are still verified as usual, but
            # ``needs_update`` will indicate that the stored hash should be
            # replaced by a more recent algorithm.
            deprecated=['auto'],
            pbkdf2_sha512__rounds=max(MIN_ROUNDS, int(cfg.get_param('password.hashing.rounds', 0))),
        )

    @contextlib.contextmanager
    def _assert_can_auth(self, user=None):
        """ Checks that the current environment even allows the current auth
        request to happen.

        The baseline implementation is a simple linear login cooldown: after
        a number of failures trying to log-in, the user (by login) is put on
        cooldown. During the cooldown period, login *attempts* are ignored
        and logged.

        :param user: user id or login, for logging purpose

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
                "Login attempt ignored for %s (user %r) on %s: "
                "%d failures since last success, last failure at %s. "
                "You can configure the number of login failures before a "
                "user is put on cooldown as well as the duration in the "
                "System Parameters. Disable this feature by setting "
                "\"base.login_cooldown_after\" to 0.",
                source, user or "?", self.env.cr.dbname, failures, previous)
            if ipaddress.ip_address(source).is_private:
                _logger.warning(
                    "The rate-limited IP address %s is classified as private "
                    "and *might* be a proxy. If your Odoo is behind a proxy, "
                    "it may be mis-configured. Check that you are running "
                    "Odoo in Proxy Mode and that the proxy is properly configured, see "
                    "https://www.odoo.com/documentation/latest/administration/install/deploy.html#https for details.",
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

    def _mfa_type(self):
        """ If an MFA method is enabled, returns its type as a string. """
        return

    def _mfa_url(self):
        """ If an MFA method is enabled, returns the URL for its second step. """
        return

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super().fields_get(allfields, attributes=attributes)

        # add self readable/writable fields
        readable_fields, writeable_fields = self._self_accessible_fields()
        missing = (writeable_fields | readable_fields).difference(res.keys())
        if allfields:
            missing = missing.intersection(allfields)
        if missing:
            self = self.sudo()  # noqa: PLW0642
            res.update({
                key: dict(values, readonly=key not in writeable_fields, searchable=False)
                for key, values in super().fields_get(sorted(missing), attributes).items()
            })
        return res

    def _get_view_postprocessed(self, view, arch, **options):
        arch, models = super()._get_view_postprocessed(view, arch, **options)
        if view == self.env.ref('base.view_users_form_simple_modif'):
            tree = etree.fromstring(arch)
            for node_field in tree.xpath('//field[@__groups_key__]'):
                if node_field.get('name') in self.SELF_READABLE_FIELDS:
                    node_field.attrib.pop('__groups_key__')
            arch = etree.tostring(tree)
        return arch, models


ResUsersPatchedInTest = ResUsers


class UsersMultiCompany(models.Model):
    _inherit = 'res.users'

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        group_multi_company_id = self.env['ir.model.data']._xmlid_to_res_id(
            'base.group_multi_company', raise_if_not_found=False)
        if group_multi_company_id:
            for user in users:
                company_count = len(user.sudo().company_ids)
                if company_count <= 1 and group_multi_company_id in user.group_ids.ids:
                    user.write({'group_ids': [Command.unlink(group_multi_company_id)]})
                elif company_count > 1 and group_multi_company_id not in user.group_ids.ids:
                    user.write({'group_ids': [Command.link(group_multi_company_id)]})
        return users

    def write(self, vals):
        res = super().write(vals)
        if 'company_ids' not in vals:
            return res
        group_multi_company_id = self.env['ir.model.data']._xmlid_to_res_id(
            'base.group_multi_company', raise_if_not_found=False)
        if group_multi_company_id:
            for user in self:
                company_count = len(user.sudo().company_ids)
                if company_count <= 1 and group_multi_company_id in user.group_ids.ids:
                    user.write({'group_ids': [Command.unlink(group_multi_company_id)]})
                elif company_count > 1 and group_multi_company_id not in user.group_ids.ids:
                    user.write({'group_ids': [Command.link(group_multi_company_id)]})
        return res

    @api.model
    def new(self, values=None, origin=None, ref=None):
        if values is None:
            values = {}
        user = super().new(values=values, origin=origin, ref=ref)
        group_multi_company_id = self.env['ir.model.data']._xmlid_to_res_id(
            'base.group_multi_company', raise_if_not_found=False)
        if group_multi_company_id:
            company_count = len(user.sudo().company_ids)
            if company_count <= 1 and group_multi_company_id in user.group_ids.ids:
                user.update({'group_ids': [Command.unlink(group_multi_company_id)]})
            elif company_count > 1 and group_multi_company_id not in user.group_ids.ids:
                user.update({'group_ids': [Command.link(group_multi_company_id)]})
        return user


class ResUsersIdentitycheck(models.TransientModel):
    """ Wizard used to re-check the user's credentials (password) and eventually
    revoke access to his account to every device he has an active session on.

    Might be useful before the more security-sensitive operations, users might be
    leaving their computer unlocked & unattended. Re-checking credentials mitigates
    some of the risk of a third party using such an unattended device to manipulate
    the account.
    """
    _name = 'res.users.identitycheck'
    _description = "Password Check Wizard"

    request = fields.Char(readonly=True, groups=fields.NO_ACCESS)
    auth_method = fields.Selection([('password', 'Password')], default=lambda self: self._get_default_auth_method())
    password = fields.Char(store=False)

    def _get_default_auth_method(self):
        return 'password'

    def _check_identity(self):
        try:
            credential = {
                'login': self.env.user.login,
                'password': self.env.context.get('password'),
                'type': 'password',
            }
            self.create_uid._check_credentials(credential, {'interactive': True})
        except AccessDenied:
            raise UserError(_("Incorrect Password, try again or click on Forgot Password to reset your password."))

    def run_check(self):
        # The password must be in the context with the key name `'password'`
        assert request, "This method can only be accessed over HTTP"
        self._check_identity()

        request.session['identity-check-last'] = time.time()
        ctx, model, ids, method, args, kwargs = json.loads(self.sudo().request)
        method = getattr(self.env(context=ctx)[model].browse(ids), method)
        assert getattr(method, '__has_check_identity', False)
        return method(*args, **kwargs)

#----------------------------------------------------------
# change password wizard
#----------------------------------------------------------


class ChangePasswordWizard(models.TransientModel):
    """ A wizard to manage the change of users' passwords. """
    _name = 'change.password.wizard'
    _description = "Change Password Wizard"
    _transient_max_hours = 0.2

    def _default_user_ids(self):
        user_ids = self.env.context.get('active_model') == 'res.users' and self.env.context.get('active_ids') or []
        return [
            Command.create({'user_id': user.id, 'user_login': user.login})
            for user in self.env['res.users'].browse(user_ids)
        ]

    user_ids = fields.One2many('change.password.user', 'wizard_id', string='Users', default=_default_user_ids)

    def change_password_button(self):
        self.ensure_one()
        self.user_ids.change_password_button()
        if self.env.user in self.user_ids.user_id:
            return {'type': 'ir.actions.client', 'tag': 'reload'}
        return {'type': 'ir.actions.act_window_close'}


class ChangePasswordUser(models.TransientModel):
    """ A model to configure users in the change password wizard. """
    _name = 'change.password.user'
    _description = 'User, Change Password Wizard'
    wizard_id = fields.Many2one('change.password.wizard', string='Wizard', required=True, ondelete='cascade')
    user_id = fields.Many2one('res.users', string='User', required=True, ondelete='cascade')
    user_login = fields.Char(string='User Login', readonly=True)
    new_passwd = fields.Char(string='New Password', default='')

    def change_password_button(self):
        for line in self:
            if line.new_passwd:
                line.user_id._change_password(line.new_passwd)
        # don't keep temporary passwords in the database longer than necessary
        self.write({'new_passwd': False})


class ChangePasswordOwn(models.TransientModel):
    _name = 'change.password.own'
    _description = "User, change own password wizard"
    _transient_max_hours = 0.1

    new_password = fields.Char(string="New Password")
    confirm_password = fields.Char(string="New Password (Confirmation)")

    @api.constrains('new_password', 'confirm_password')
    def _check_password_confirmation(self):
        if self.confirm_password != self.new_password:
            raise ValidationError(_("The new password and its confirmation must be identical."))

    @check_identity
    def change_password(self):
        self.env.user._change_password(self.new_password)
        self.unlink()
        # reload to avoid a session expired error
        # would be great to update the session id in-place, but it seems dicey
        return {'type': 'ir.actions.client', 'tag': 'reload'}

# API keys support
API_KEY_SIZE = 20 # in bytes
INDEX_SIZE = 8 # in hex digits, so 4 bytes, or 20% of the key
KEY_CRYPT_CONTEXT = CryptContext(
    # default is 29000 rounds which is 25~50ms, which is probably unnecessary
    # given in this case all the keys are completely random data: dictionary
    # attacks on API keys isn't much of a concern
    ['pbkdf2_sha512'], pbkdf2_sha512__rounds=6000,
)
DEFAULT_PROGRAMMATIC_API_KEYS_LIMIT = 10  # programmatic API key creation is refused if the user already has at least this amount of API keys


class ResUsersApikeys(models.Model):
    _name = 'res.users.apikeys'
    _description = 'Users API Keys'
    _auto = False # so we can have a secret column
    _allow_sudo_commands = False

    name = fields.Char("Description", required=True, readonly=True)
    user_id = fields.Many2one('res.users', index=True, required=True, readonly=True, ondelete="cascade")
    scope = fields.Char("Scope", readonly=True)
    create_date = fields.Datetime("Creation Date", readonly=True)
    expiration_date = fields.Datetime("Expiration Date", readonly=True)

    def init(self):
        table = SQL.identifier(self._table)
        self.env.cr.execute(SQL("""
        CREATE TABLE IF NOT EXISTS %(table)s (
            id serial primary key,
            name varchar not null,
            user_id integer not null REFERENCES res_users(id) ON DELETE CASCADE,
            scope varchar,
            expiration_date timestamp without time zone,
            index varchar(%(index_size)s) not null CHECK (char_length(index) = %(index_size)s),
            key varchar not null,
            create_date timestamp without time zone DEFAULT (now() at time zone 'utc')
        )
        """, table=table, index_size=INDEX_SIZE))

        index_name = self._table + "_user_id_index_idx"
        if len(index_name) > 63:
            # unique determinist index name
            index_name = self._table[:50] + "_idx_" + sha256(self._table.encode()).hexdigest()[:8]
        self.env.cr.execute(SQL(
            "CREATE INDEX IF NOT EXISTS %s ON %s (user_id, index)",
            SQL.identifier(index_name),
            table,
        ))

    @check_identity
    def remove(self):
        return self._remove()

    def _remove(self):
        """Use the remove() method to remove an API Key. This method implement logic,
        but won't check the identity (mainly used to remove trusted devices)"""
        if not self:
            return {'type': 'ir.actions.act_window_close'}
        if self.env.is_system() or self.mapped('user_id') == self.env.user:
            ip = request.httprequest.environ['REMOTE_ADDR'] if request else 'n/a'
            _logger.info("API key(s) removed: scope: <%s> for '%s' (#%s) from %s",
               self.mapped('scope'), self.env.user.login, self.env.uid, ip)
            self.sudo().unlink()
            self.env.registry.clear_cache()
            return {'type': 'ir.actions.act_window_close'}
        raise AccessError(_("You can not remove API keys unless they're yours or you are a system user"))

    def _check_credentials(self, *, scope, key):
        assert scope and key, "scope and key required"
        index = key[:INDEX_SIZE]
        self.env.cr.execute('''
            SELECT user_id, key
            FROM {} INNER JOIN res_users u ON (u.id = user_id)
            WHERE
                u.active and index = %s
                AND (scope IS NULL OR scope = %s)
                AND (
                    expiration_date IS NULL OR
                    expiration_date >= now() at time zone 'utc'
                )
        '''.format(self._table),
        [index, scope])
        for user_id, current_key in self.env.cr.fetchall():
            if key and KEY_CRYPT_CONTEXT.verify(key, current_key):
                return user_id

    def _check_expiration_date(self, date):
        # To be in a sudoed environment or to be an administrator
        # to create a persistent key (no expiration date) or
        # to exceed the maximum duration determined by the user's privileges.
        if self.env.is_system():
            return
        if not date:
            raise ValidationError(_("The API key must have an expiration date"))
        max_duration = max(group.api_key_duration for group in self.env.user.all_group_ids) or 1.0
        if date > datetime.datetime.now() + datetime.timedelta(days=max_duration):
            raise ValidationError(_("You cannot exceed %(duration)s days.", duration=max_duration))

    def _generate(self, scope, name, expiration_date):
        """Generates an api key.
        :param str scope: the scope of the key. If None, the key will give access to any rpc.
        :param str name: the name of the key, mainly intended to be displayed in the UI.
        :param date expiration_date: the expiration date of the key.
        :return: str: the key.

        Note:
        This method must be called in sudo to use a duration
        greater than that allowed by the user's privileges.
        For a persistent key (infinite duration), no value for expiration date.
        """
        self._check_expiration_date(expiration_date)
        # no need to clear the LRU when *adding* a key, only when removing
        k = binascii.hexlify(os.urandom(API_KEY_SIZE)).decode()
        self.env.cr.execute("""
        INSERT INTO {table} (name, user_id, scope, expiration_date, key, index)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
        """.format(table=self._table),
        [name, self.env.user.id, scope, expiration_date or None, KEY_CRYPT_CONTEXT.hash(k), k[:INDEX_SIZE]])

        ip = request.httprequest.environ['REMOTE_ADDR'] if request else 'n/a'
        _logger.info("%s generated: scope: <%s> for '%s' (#%s) from %s",
            self._description, scope, self.env.user.login, self.env.uid, ip)

        return k

    def _ensure_can_manage_keys_programmatically(self):
        # Administrators would not be restricted by the ICP check alone,
        # as they could temporarily enable the setting via set_param().
        # However, this is considered bad practice because it would create a time window
        # where anyone could manage API keys programmatically.
        # Additionally, the enable / call / restore process involves three distinct calls,
        # which is not atomic and prone to errors (e.g., server unavailability during restore),
        # potentially leaving the configuration enabled for all users.
        # To avoid this, an exception is made for Administrators.
        # However, if programmatic API key management were to be enabled by default,
        # this exception should be removed, as disabling the feature should be global.
        ICP = self.env['ir.config_parameter'].sudo()
        programmatic_api_keys_enabled = str2bool(ICP.get_param('base.enable_programmatic_api_keys'), False)
        if not (self.env.is_system() or programmatic_api_keys_enabled):
            raise UserError(_("Programmatic API keys are not enabled"))

    @api.model
    def generate(self, key, scope, name, expiration_date):
        """
        Generate a new API key with an existing API key.
        The provided `key` must be an existing API key that belongs to the current user.
        Its scope must be compatible with `scope`.
        The `expiration_date` must be allowed for the user's group.

        To renew a key, generate the new one, store it, and then call `revoke` on the previous one.
        """
        self._ensure_can_manage_keys_programmatically()

        with self.env['res.users']._assert_can_auth(user=key[:INDEX_SIZE]):
            if not isinstance(expiration_date, datetime.datetime):
                expiration_date = fields.Datetime.from_string(expiration_date)

            nb_keys = self.search_count([('user_id', '=', self.env.uid),
                                         '|', ('expiration_date', '=', False), ('expiration_date', '>=', self.env.cr.now())])
            try:
                ICP = self.env['ir.config_parameter'].sudo()
                nb_keys_limit = int(ICP.get_param('base.programmatic_api_keys_limit', DEFAULT_PROGRAMMATIC_API_KEYS_LIMIT))
            except ValueError:
                _logger.warning("Invalid value for 'base.programmatic_api_keys_limit', using default value.")
                nb_keys_limit = DEFAULT_PROGRAMMATIC_API_KEYS_LIMIT
            if nb_keys >= nb_keys_limit:
                raise UserError(_('Limit of %s API keys is reached for programmatic creation', nb_keys_limit))

            # Scope compatibility rules:
            # - A global key can generate credentials for any scope (including global).
            # - A scoped key can only generate credentials for its own scope.
            #
            # This is enforced in _check_credentials by validating scope usage,
            # and the validated scope is then reused when calling _generate.

            uid = self.env['res.users.apikeys']._check_credentials(scope=scope or 'rpc', key=key)
            if not uid or uid != self.env.uid:
                raise AccessDenied(_("The provided API key is invalid or does not belong to the current user."))
            new_key = self._generate(scope, name, expiration_date)
            _logger.info("%s %r generated from %r", self._description, new_key[:INDEX_SIZE], key[:INDEX_SIZE])

            return new_key

    @api.model
    def revoke(self, key):
        """
        Revoke an existing API key.
        If it exists, the `key` will be removed from the server.
        """
        self._ensure_can_manage_keys_programmatically()
        assert key, "key required"
        with self.env['res.users']._assert_can_auth(user=key[:INDEX_SIZE]):
            self.env.cr.execute(SQL('''
                SELECT id, key
                FROM %(table)s
                WHERE
                    index = %(index)s
                    AND (
                        expiration_date IS NULL OR
                        expiration_date >= now() at time zone 'utc'
                    )
            ''', table=SQL.identifier(self._table), index=key[:INDEX_SIZE]))
            for key_id, current_key in self.env.cr.fetchall():
                if key and KEY_CRYPT_CONTEXT.verify(key, current_key):
                    self.env['res.users.apikeys'].browse(key_id)._remove()
                    return True
            raise AccessDenied(_("The provided API key is invalid."))

    @api.autovacuum
    def _gc_user_apikeys(self):
        self.env.cr.execute(SQL("""
            DELETE FROM %s
            WHERE
                expiration_date IS NOT NULL AND
                expiration_date < now() at time zone 'utc'
        """, SQL.identifier(self._table)))
        _logger.info("GC %r delete %d entries", self._name, self.env.cr.rowcount)


class ResUsersApikeysDescription(models.TransientModel):
    _name = 'res.users.apikeys.description'
    _description = 'API Key Description'

    def _selection_duration(self):
        # duration value is a string representing the number of days.
        durations = [
            ('1', '1 Day'),
            ('7', '1 Week'),
            ('30', '1 Month'),
            ('90', '3 Months'),
            ('180', '6 Months'),
            ('365', '1 Year'),
        ]
        persistent_duration = ('0', 'Persistent Key')  # Magic value to detect an infinite duration
        custom_duration = ('-1', 'Custom Date')  # Will force the user to enter a date manually
        if self.env.is_system():
            return durations + [persistent_duration, custom_duration]
        max_duration = max(group.api_key_duration for group in self.env.user.all_group_ids) or 1.0
        return list(filter(
            lambda duration: int(duration[0]) <= max_duration, durations
        )) + [custom_duration]

    name = fields.Char("Description", required=True)
    duration = fields.Selection(
        selection='_selection_duration', string='Duration', required=True,
        default=lambda self: self._selection_duration()[0][0]
    )
    expiration_date = fields.Datetime('Expiration Date', compute='_compute_expiration_date', store=True, readonly=False)

    @api.depends('duration')
    def _compute_expiration_date(self):
        for record in self:
            duration = int(record.duration)
            if duration >= 0:
                record.expiration_date = (
                    fields.Date.today() + datetime.timedelta(days=duration)
                    if int(record.duration)
                    else None
                )

    @api.onchange('expiration_date')
    def _onchange_expiration_date(self):
        try:
            self.env['res.users.apikeys']._check_expiration_date(self.expiration_date)
        except UserError as error:
            warning = {
                'type': 'notification',
                'title': _('The API key duration is not correct.'),
                'message': error.args[0]
            }
            return {'warning': warning}

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        self.env['res.users.apikeys']._check_expiration_date(res.expiration_date)
        return res

    @check_identity
    def make_key(self):
        # only create keys for users who can delete their keys
        self.check_access_make_key()

        description = self.sudo()
        k = self.env['res.users.apikeys']._generate(None, description.name, self.expiration_date)
        description.unlink()

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'res.users.apikeys.show',
            'name': _('API Key Ready'),
            'views': [(False, 'form')],
            'target': 'new',
            'context': {
                'default_key': k,
            }
        }

    def check_access_make_key(self):
        if not self.env.user._is_internal():
            raise AccessError(_("Only internal users can create API keys"))


class ResUsersApikeysShow(models.AbstractModel):
    _name = 'res.users.apikeys.show'
    _description = 'Show API Key'

    # the field 'id' is necessary for the onchange that returns the value of 'key'
    id = fields.Id()
    key = fields.Char(readonly=True)
