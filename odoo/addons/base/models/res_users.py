# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import binascii
import contextlib
import datetime
import hmac
import ipaddress
import itertools
import json
import logging
import os
import time
from collections import defaultdict
from functools import wraps
from hashlib import sha256
from itertools import chain, repeat
from markupsafe import Markup

import babel.core
import pytz
from lxml import etree
from lxml.builder import E
from passlib.context import CryptContext as _CryptContext
from psycopg2 import sql

from odoo import api, fields, models, tools, SUPERUSER_ID, _, Command
from odoo.addons.base.models.ir_model import MODULE_UNINSTALL_FLAG
from odoo.exceptions import AccessDenied, AccessError, UserError, ValidationError
from odoo.http import request, DEFAULT_LANG
from odoo.osv import expression
from odoo.service.db import check_super
from odoo.tools import is_html_empty, partition, collections, frozendict, lazy_property
from odoo.tools.misc import OrderedSet

_logger = logging.getLogger(__name__)

class CryptContext:
    def __init__(self, *args, **kwargs):
        self.__obj__ = _CryptContext(*args, **kwargs)

    @property
    def encrypt(self):
        # deprecated alias
        return self.hash

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


# Only users who can modify the user (incl. the user herself) see the real contents of these fields
USER_PRIVATE_FIELDS = []
MIN_ROUNDS = 600_000
concat = chain.from_iterable

#
# Functions for manipulating boolean and selection pseudo-fields
#
def name_boolean_group(id):
    return 'in_group_' + str(id)

def name_selection_groups(ids):
    return 'sel_groups_' + '_'.join(str(it) for it in sorted(ids))

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
            if command[0] in (Command.UPDATE, Command.LINK):
                ids.append(command[1])
            elif command[0] == Command.CLEAR:
                ids = []
            elif command[0] == Command.SET:
                ids = list(command[2])
        else:
            ids.append(command)
    return ids

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
    def wrapped(self):
        if not request:
            raise UserError(_("This method can only be accessed over HTTP"))

        if request.session.get('identity-check-last', 0) > time.time() - 10 * 60:
            # update identity-check-last like github?
            return fn(self)

        w = self.sudo().env['res.users.identitycheck'].create({
            'request': json.dumps([
                { # strip non-jsonable keys (e.g. mapped to recordsets like binary_field_real_user)
                    k: v for k, v in self.env.context.items()
                    if _jsonable(v)
                },
                self._name,
                self.ids,
                fn.__name__
            ])
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'res.users.identitycheck',
            'res_id': w.id,
            'name': _("Security Control"),
            'target': 'new',
            'views': [(False, 'form')],
        }
    wrapped.__has_check_identity = True
    return wrapped

#----------------------------------------------------------
# Basic res.groups and res.users
#----------------------------------------------------------

class Groups(models.Model):
    _name = "res.groups"
    _description = "Access Groups"
    _rec_name = 'full_name'
    _order = 'name'
    _allow_sudo_commands = False

    name = fields.Char(required=True, translate=True)
    users = fields.Many2many('res.users', 'res_groups_users_rel', 'gid', 'uid')
    model_access = fields.One2many('ir.model.access', 'group_id', string='Access Controls', copy=True)
    rule_groups = fields.Many2many('ir.rule', 'rule_group_rel',
        'group_id', 'rule_group_id', string='Rules', domain="[('global', '=', False)]")
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

    @api.constrains('users')
    def _check_one_user_type(self):
        self.users._check_one_user_type()

    @api.ondelete(at_uninstall=False)
    def _unlink_except_settings_group(self):
        classified = self.env['res.config.settings']._get_classified_fields()
        for _name, _groups, implied_group in classified['group']:
            if implied_group.id in self.ids:
                raise ValidationError(_('You cannot delete a group linked with a settings field.'))

    @api.depends('category_id.name', 'name')
    def _compute_full_name(self):
        # Important: value must be stored in environment of group, not group1!
        for group, group1 in zip(self, self.sudo()):
            if group1.category_id:
                group.full_name = '%s / %s' % (group1.category_id.name, group1.name)
            else:
                group.full_name = group1.name

    def _search_full_name(self, operator, operand):
        lst = True
        if isinstance(operand, bool):
            return [('name', operator, operand)]
        if isinstance(operand, str):
            lst = False
            operand = [operand]
        where = []
        for group in operand:
            values = [v for v in group.split('/') if v]
            group_name = values.pop().strip()
            category_name = values and '/'.join(values).strip() or group_name
            group_domain = [('name', operator, lst and [group_name] or group_name)]
            category_ids = self.env['ir.module.category'].sudo()._search(
                [('name', operator, [category_name] if lst else category_name)])
            category_domain = [('category_id', 'in', category_ids)]
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

    def copy(self, default=None):
        self.ensure_one()
        chosen_name = default.get('name') if default else ''
        default_name = chosen_name or _('%s (copy)', self.name)
        default = dict(default or {}, name=default_name)
        return super(Groups, self).copy(default)

    def write(self, vals):
        if 'name' in vals:
            if vals['name'].startswith('-'):
                raise UserError(_('The name of the group can not start with "-"'))
        # invalidate caches before updating groups, since the recomputation of
        # field 'share' depends on method has_group()
        # DLE P139
        if self.ids:
            self.env['ir.model.access'].call_cache_clearing_methods()
        return super(Groups, self).write(vals)

    def _ensure_xml_id(self):
        """Return the groups external identifiers, creating the external identifier for groups missing one"""
        result = self.get_external_id()
        missings = {group_id: f'__custom__.group_{group_id}' for group_id, ext_id in result.items() if not ext_id}
        if missings:
            self.env['ir.model.data'].sudo().create(
                [
                    {
                        'name': name.split('.')[1],
                        'model': 'res.groups',
                        'res_id': group_id,
                        'module': name.split('.')[0],
                    }
                    for group_id, name in missings.items()
                ]
            )
            result.update(missings)

        return result


class ResUsersLog(models.Model):
    _name = 'res.users.log'
    _order = 'id desc'
    _description = 'Users Log'
    # Currenly only uses the magical fields: create_uid, create_date,
    # for recording logins. To be extended for other uses (chat presence, etc.)

    @api.autovacuum
    def _gc_user_logs(self):
        self._cr.execute("""
            DELETE FROM res_users_log log1 WHERE EXISTS (
                SELECT 1 FROM res_users_log log2
                WHERE log1.create_uid = log2.create_uid
                AND log1.create_date < log2.create_date
            )
        """)
        _logger.info("GC'd %d user log entries", self._cr.rowcount)


class Users(models.Model):
    """ User class. A res.users record models an OpenERP user and is different
        from an employee.

        res.users class now inherits from res.partner. The partner model is
        used to store the data related to the partner: lang, name, address,
        avatar, ... The user model is now dedicated to technical data.
    """
    _name = "res.users"
    _description = 'User'
    _inherits = {'res.partner': 'partner_id'}
    _order = 'name, login'
    _allow_sudo_commands = False

    @property
    def SELF_READABLE_FIELDS(self):
        """ The list of fields a user can read on their own user record.
        In order to add fields, please override this property on model extensions.
        """
        return [
            'signature', 'company_id', 'login', 'email', 'name', 'image_1920',
            'image_1024', 'image_512', 'image_256', 'image_128', 'lang', 'tz',
            'tz_offset', 'groups_id', 'partner_id', '__last_update', 'action_id',
            'avatar_1920', 'avatar_1024', 'avatar_512', 'avatar_256', 'avatar_128',
            'share',
        ]

    @property
    def SELF_WRITEABLE_FIELDS(self):
        """ The list of fields a user can write on their own user record.
        In order to add fields, please override this property on model extensions.
        """
        return ['signature', 'action_id', 'company_id', 'email', 'name', 'image_1920', 'lang', 'tz']

    def _default_groups(self):
        """Default groups for employees

        All the groups of the Template User
        """
        default_user = self.env.ref('base.default_user', raise_if_not_found=False)
        return default_user.sudo().groups_id if default_user else []

    partner_id = fields.Many2one('res.partner', required=True, ondelete='restrict', auto_join=True, index=True,
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
    signature = fields.Html(string="Email Signature", compute='_compute_signature', readonly=False, store=True)
    active = fields.Boolean(default=True)
    active_partner = fields.Boolean(related='partner_id.active', readonly=True, string="Partner is Active")
    action_id = fields.Many2one('ir.actions.actions', string='Home Action',
        help="If specified, this action will be opened at log on for this user, in addition to the standard menu.")
    groups_id = fields.Many2many('res.groups', 'res_groups_users_rel', 'uid', 'gid', string='Groups', default=lambda s: s._default_groups())
    log_ids = fields.One2many('res.users.log', 'create_uid', string='User log entries')
    login_date = fields.Datetime(related='log_ids.create_date', string='Latest authentication', readonly=False)
    share = fields.Boolean(compute='_compute_share', compute_sudo=True, string='Share User', store=True,
         help="External user with limited access, created only for the purpose of sharing data.")
    companies_count = fields.Integer(compute='_compute_companies_count', string="Number of Companies")
    tz_offset = fields.Char(compute='_compute_tz_offset', string='Timezone offset', invisible=True)

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
        cr.execute(r"""
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
            self._set_encrypted_password(user.id, ctx.hash(user.password))

    def _set_encrypted_password(self, uid, pw):
        assert self._crypt_context().identify(pw) != 'plaintext'

        self.env.cr.execute(
            'UPDATE res_users SET password=%s WHERE id=%s',
            (pw, uid)
        )
        self.browse(uid).invalidate_recordset(['password'])

    def _check_credentials(self, password, env):
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

    @api.depends('name')
    def _compute_signature(self):
        for user in self.filtered(lambda user: user.name and is_html_empty(user.signature)):
            user.signature = Markup('<p>--<br />%s</p>') % user['name']

    @api.depends('groups_id')
    def _compute_share(self):
        user_group_id = self.env['ir.model.data']._xmlid_to_res_id('base.group_user')
        internal_users = self.filtered_domain([('groups_id', 'in', [user_group_id])])
        internal_users.share = False
        (self - internal_users).share = True

    @api.depends('company_id')
    def _compute_companies_count(self):
        self.companies_count = self.env['res.company'].sudo().search_count([])

    @api.depends('tz')
    def _compute_tz_offset(self):
        for user in self:
            user.tz_offset = datetime.datetime.now(pytz.timezone(user.tz or 'GMT')).strftime('%z')

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

    @api.onchange('parent_id')
    def onchange_parent_id(self):
        return self.partner_id.onchange_parent_id()

    def _read(self, fields):
        super(Users, self)._read(fields)
        if set(USER_PRIVATE_FIELDS).intersection(fields):
            if self.check_access_rights('write', raise_exception=False):
                return
            for record in self:
                for f in USER_PRIVATE_FIELDS:
                    try:
                        record._cache[f]
                        record._cache[f] = '********'
                    except Exception:
                        # skip SpecialValue (e.g. for missing record or access right)
                        pass

    @api.constrains('company_id', 'company_ids', 'active')
    def _check_company(self):
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
            readable = self.SELF_READABLE_FIELDS
            for key in fields:
                if not (key in readable or key.startswith('context_')):
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

    def _apply_groups_to_existing_employees(self):
        """ Should new groups be added to existing employees?

        If the template user is being modified, the groups should be applied to
        every other base_user users
        """
        default_user = self.env.ref('base.default_user', raise_if_not_found=False)
        return default_user and default_user in self

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
            writeable = self.SELF_WRITEABLE_FIELDS
            for key in list(values):
                if not (key in writeable or key.startswith('context_')):
                    break
            else:
                if 'company_id' in values:
                    if values['company_id'] not in self.env.user.company_ids.ids:
                        del values['company_id']
                # safe fields only, so we write as super-user to bypass access rights
                self = self.sudo().with_context(binary_field_real_user=self.env.user)

        old_groups = []
        if 'groups_id' in values and self._apply_groups_to_existing_employees():
            # if modify groups_id content, compute the delta of groups to apply
            # the new ones to other existing users
            old_groups = self._default_groups()

        res = super(Users, self).write(values)

        if old_groups:
            # new elements in _default_groups() means new groups for default users
            # that needs to be added to existing ones as well for consistency
            added_groups = self._default_groups() - old_groups
            if added_groups:
                internal_users = self.env.ref('base.group_user').users - self
                internal_users.write({'groups_id': [Command.link(gid) for gid in added_groups.ids]})

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
            for env in list(self.env.transaction.envs):
                if env.user in self:
                    lazy_property.reset_all(env)

        # clear caches linked to the users
        if self.ids and 'groups_id' in values:
            # DLE P139: Calling invalidate_cache on a new, well you lost everything as you wont be able to take it back from the cache
            # `test_00_equipment_multicompany_user`
            self.env['ir.model.access'].call_cache_clearing_methods()

        # per-method / per-model caches have been removed so the various
        # clear_cache/clear_caches methods pretty much just end up calling
        # Registry._clear_cache
        invalidation_fields = self._get_invalidation_fields()
        if (invalidation_fields & values.keys()) or any(key.startswith('context_') for key in values):
            self.clear_caches()

        return res

    @api.ondelete(at_uninstall=True)
    def _unlink_except_master_data(self):
        portal_user_template = self.env.ref('base.template_portal_user_id', False)
        default_user_template = self.env.ref('base.default_user', False)
        if SUPERUSER_ID in self.ids:
            raise UserError(_('You can not remove the admin user as it is used internally for resources created by Odoo (updates, module installation, ...)'))
        user_admin = self.env.ref('base.user_admin', raise_if_not_found=False)
        if user_admin and user_admin in self:
            raise UserError(_('You cannot delete the admin user because it is utilized in various places (such as security configurations,...). Instead, archive it.'))
        self.clear_caches()
        if (portal_user_template and portal_user_template in self) or (default_user_template and default_user_template in self):
            raise UserError(_('Deleting the template users is not allowed. Deleting this profile will compromise critical functionalities.'))

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
        return user_ids

    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {})
        if ('name' not in default) and ('partner_id' not in default):
            default['name'] = _("%s (copy)", self.name)
        if 'login' not in default:
            default['login'] = _("%s (copy)", self.login)
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

        context = {
            key: values[name]
            for name, key in name_to_key.items()
        }

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

    def check_super(self, passwd):
        return check_super(passwd)

    @api.model
    def _get_invalidation_fields(self):
        return {
            'groups_id', 'active', 'lang', 'tz', 'company_id', 'company_ids',
            *USER_PRIVATE_FIELDS,
            *self._get_session_token_fields()
        }

    @api.model
    def _update_last_login(self):
        # only create new records to avoid any side-effect on concurrent transactions
        # extra records will be deleted by the periodical garbage collection
        self.env['res.users.log'].create({}) # populated by defaults

    @api.model
    def _get_login_domain(self, login):
        return [('login', '=', login)]

    @api.model
    def _get_email_domain(self, email):
        return [('email', '=', email)]

    @api.model
    def _get_login_order(self):
        return self._order

    @classmethod
    def _login(cls, db, login, password, user_agent_env):
        if not password:
            raise AccessDenied()
        ip = request.httprequest.environ['REMOTE_ADDR'] if request else 'n/a'
        try:
            with cls.pool.cursor() as cr:
                self = api.Environment(cr, SUPERUSER_ID, {})[cls._name]
                with self._assert_can_auth(user=login):
                    user = self.search(self._get_login_domain(login), order=self._get_login_order(), limit=1)
                    if not user:
                        raise AccessDenied()
                    user = user.with_user(user)
                    user._check_credentials(password, user_agent_env)
                    tz = request.httprequest.cookies.get('tz') if request else None
                    if tz in pytz.all_timezones and (not user.tz or not user.login_date):
                        # first login or missing tz -> set tz to browser tz
                        user.tz = tz
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
        uid = cls._login(db, login, password, user_agent_env=user_agent_env)
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
    @tools.ormcache('uid', 'passwd')
    def check(cls, db, uid, passwd):
        """Verifies that the given (uid, password) is authorized for the database ``db`` and
           raise an exception if it is not."""
        if not passwd:
            # empty passwords disallowed for obvious security reasons
            raise AccessDenied()

        with contextlib.closing(cls.pool.cursor()) as cr:
            self = api.Environment(cr, uid, {})[cls._name]
            with self._assert_can_auth(user=uid):
                if not self.env.user.active:
                    raise AccessDenied()
                self._check_credentials(passwd, {'interactive': False})

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
            self.clear_caches()
            return False
        data_fields = self.env.cr.fetchone()
        # generate hmac key
        key = (u'%s' % (data_fields,)).encode('utf-8')
        # hmac the session id
        data = sid.encode('utf-8')
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
        self._check_credentials(old_passwd, {'interactive': True})

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

    @check_identity
    def preference_change_password(self):
        return {
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_model': 'change.password.own',
            'view_mode': 'form',
        }

    @api.model
    def has_group(self, group_ext_id):
        # use singleton's id if called on a non-empty recordset, otherwise
        # context uid
        uid = self.id
        if uid and uid != self._uid:
            self = self.with_user(uid)
        return self._has_group(group_ext_id)

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
                            (SELECT res_id FROM ir_model_data WHERE module=%s AND name=%s AND model='res.groups')""",
                         (self._uid, module, ext_id))
        return bool(self._cr.fetchone())

    def _action_show(self):
        """If self is a singleton, directly access the form view. If it is a recordset, open a tree view"""
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

    def _is_internal(self):
        self.ensure_one()
        return not self.sudo().share

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

    @tools.ormcache()
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
                    "https://www.odoo.com/documentation/16.0/administration/install/deploy.html#https for details.",
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
        compute='_compute_trans_implied', recursive=True)

    @api.depends('implied_ids.trans_implied_ids')
    def _compute_trans_implied(self):
        # Compute the transitive closure recursively. Note that the performance
        # is good, because the record cache behaves as a memo (the field is
        # never computed twice on a given group.)
        for g in self:
            g.trans_implied_ids = g.implied_ids | g.implied_ids.trans_implied_ids

    @api.model_create_multi
    def create(self, vals_list):
        user_ids_list = [vals.pop('users', None) for vals in vals_list]
        groups = super(GroupsImplied, self).create(vals_list)
        for group, user_ids in zip(groups, user_ids_list):
            if user_ids:
                # delegate addition of users to add implied groups
                group.write({'users': user_ids})
        return groups

    def write(self, values):
        res = super(GroupsImplied, self).write(values)
        if values.get('users') or values.get('implied_ids'):
            # add all implied groups (to all users of each group)
            updated_group_ids = OrderedSet()
            updated_user_ids = OrderedSet()
            for group in self:
                self._cr.execute("""
                    WITH RECURSIVE group_imply(gid, hid) AS (
                        SELECT gid, hid
                          FROM res_groups_implied_rel
                         UNION
                        SELECT i.gid, r.hid
                          FROM res_groups_implied_rel r
                          JOIN group_imply i ON (i.hid = r.gid)
                    )
                    INSERT INTO res_groups_users_rel (gid, uid)
                         SELECT i.hid, r.uid
                           FROM group_imply i, res_groups_users_rel r
                          WHERE r.gid = i.gid
                            AND i.gid = %(gid)s
                         EXCEPT
                         SELECT r.gid, r.uid
                           FROM res_groups_users_rel r
                           JOIN group_imply i ON (r.gid = i.hid)
                          WHERE i.gid = %(gid)s
                    RETURNING gid, uid
                """, dict(gid=group.id))
                updated = self.env.cr.fetchall()
                gids, uids = zip(*updated) if updated else ([], [])
                updated_group_ids.update(gids)
                updated_user_ids.update(uids)
            # notify the ORM about the updated users and groups
            updated_groups = self.env['res.groups'].browse(updated_group_ids)
            updated_groups.invalidate_recordset(['users'])
            updated_groups.modified(['users'])
            updated_users = self.env['res.users'].browse(updated_user_ids)
            updated_users.invalidate_recordset(['groups_id'])
            updated_users.modified(['groups_id'])
            # explicitly check constraints
            updated_groups._validate_fields(['users'])
            updated_users._validate_fields(['groups_id'])
        return res

    def _apply_group(self, implied_group):
        """ Add the given group to the groups implied by the current group
        :param implied_group: the implied group to add
        """
        groups = self.filtered(lambda g: implied_group not in g.implied_ids)
        groups.write({'implied_ids': [Command.link(implied_group.id)]})

    def _remove_group(self, implied_group):
        """ Remove the given group from the implied groups of the current group
        :param implied_group: the implied group to remove
        """
        groups = self.filtered(lambda g: implied_group in g.implied_ids)
        if groups:
            groups.write({'implied_ids': [Command.unlink(implied_group.id)]})
            # if user belongs to implied_group thanks to another group, don't remove him
            # this avoids readding the template user and triggering the mechanism at 121cd0d6084cb28
            users_to_unlink = [
                user
                for user in groups.with_context(active_test=False).users
                if implied_group not in (user.groups_id - implied_group).trans_implied_ids
            ]
            if users_to_unlink:
                # do not remove inactive users (e.g. default)
                implied_group.with_context(active_test=False).write(
                    {'users': [Command.unlink(user.id) for user in users_to_unlink]})

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
                values['groups_id'] = self._fields['groups_id'].convert_to_write(gs, user)
        return super(UsersImplied, self).create(vals_list)

    def write(self, values):
        if not values.get('groups_id'):
            return super(UsersImplied, self).write(values)
        users_before = self.filtered(lambda u: u._is_internal())
        res = super(UsersImplied, self).write(values)
        demoted_users = users_before.filtered(lambda u: not u._is_internal())
        if demoted_users:
            # demoted users are restricted to the assigned groups only
            vals = {'groups_id': [Command.clear()] + values['groups_id']}
            super(UsersImplied, demoted_users).write(vals)
        # add implied groups for all users (in batches)
        users_batch = defaultdict(self.browse)
        for user in self:
            users_batch[user.groups_id] += user
        for groups, users in users_batch.items():
            gs = set(concat(g.trans_implied_ids for g in groups))
            vals = {'groups_id': [Command.link(g.id) for g in gs]}
            super(UsersImplied, users).write(vals)
        return res

#
# Virtual checkbox and selection for res.user form view
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
#

class GroupsView(models.Model):
    _inherit = 'res.groups'

    @api.model_create_multi
    def create(self, vals_list):
        groups = super().create(vals_list)
        self._update_user_groups_view()
        # actions.get_bindings() depends on action records
        self.env['ir.actions.actions'].clear_caches()
        return groups

    def write(self, values):
        # determine which values the "user groups view" depends on
        VIEW_DEPS = ('category_id', 'implied_ids')
        view_values0 = [g[name] for name in VIEW_DEPS if name in values for g in self]
        res = super(GroupsView, self).write(values)
        # update the "user groups view" only if necessary
        view_values1 = [g[name] for name in VIEW_DEPS if name in values for g in self]
        if view_values0 != view_values1:
            self._update_user_groups_view()
        # actions.get_bindings() depends on action records
        self.env['ir.actions.actions'].clear_caches()
        return res

    def unlink(self):
        res = super(GroupsView, self).unlink()
        self._update_user_groups_view()
        # actions.get_bindings() depends on action records
        self.env['ir.actions.actions'].clear_caches()
        return res

    def _get_hidden_extra_categories(self):
        return ['base.module_category_hidden', 'base.module_category_extra', 'base.module_category_usability']

    @api.model
    def _update_user_groups_view(self):
        """ Modify the view with xmlid ``base.user_groups_view``, which inherits
            the user form view, and introduces the reified group fields.
        """
        # remove the language to avoid translations, it will be handled at the view level
        self = self.with_context(lang=None)

        # We have to try-catch this, because at first init the view does not
        # exist but we are already creating some basic groups.
        view = self.env.ref('base.user_groups_view', raise_if_not_found=False)
        if not (view and view._name == 'ir.ui.view'):
            return

        if self._context.get('install_filename') or self._context.get(MODULE_UNINSTALL_FLAG):
            # use a dummy view during install/upgrade/uninstall
            xml = E.field(name="groups_id", position="after")

        else:
            group_no_one = view.env.ref('base.group_no_one')
            group_employee = view.env.ref('base.group_user')
            xml0, xml1, xml2, xml3, xml4 = [], [], [], [], []
            xml_by_category = {}
            xml1.append(E.separator(string='User Type', colspan="2", groups='base.group_no_one'))

            user_type_field_name = ''
            user_type_readonly = str({})
            sorted_tuples = sorted(self.get_groups_by_application(),
                                   key=lambda t: t[0].xml_id != 'base.module_category_user_type')
            for app, kind, gs, category_name in sorted_tuples:  # we process the user type first
                attrs = {}
                # hide groups in categories 'Hidden' and 'Extra' (except for group_no_one)
                if app.xml_id in self._get_hidden_extra_categories():
                    attrs['groups'] = 'base.group_no_one'

                # User type (employee, portal or public) is a separated group. This is the only 'selection'
                # group of res.groups without implied groups (with each other).
                if app.xml_id == 'base.module_category_user_type':
                    # application name with a selection field
                    field_name = name_selection_groups(gs.ids)
                    # test_reified_groups, put the user category type in invisible
                    # as it's used in domain of attrs of other fields,
                    # and the normal user category type field node is wrapped in a `groups="base.no_one"`,
                    # and is therefore removed when not in debug mode.
                    xml0.append(E.field(name=field_name, invisible="1", on_change="1"))
                    user_type_field_name = field_name
                    user_type_readonly = str({'readonly': [(user_type_field_name, '!=', group_employee.id)]})
                    attrs['widget'] = 'radio'
                    # Trigger the on_change of this "virtual field"
                    attrs['on_change'] = '1'
                    xml1.append(E.field(name=field_name, **attrs))
                    xml1.append(E.newline())

                elif kind == 'selection':
                    # application name with a selection field
                    field_name = name_selection_groups(gs.ids)
                    attrs['attrs'] = user_type_readonly
                    attrs['on_change'] = '1'
                    if category_name not in xml_by_category:
                        xml_by_category[category_name] = []
                        xml_by_category[category_name].append(E.newline())
                    xml_by_category[category_name].append(E.field(name=field_name, **attrs))
                    xml_by_category[category_name].append(E.newline())
                    # add duplicate invisible field so default values are saved on create
                    if attrs.get('groups') == 'base.group_no_one':
                        xml0.append(E.field(name=field_name, **dict(attrs, invisible="1", groups='!base.group_no_one')))

                else:
                    # application separator with boolean fields
                    app_name = app.name or 'Other'
                    xml4.append(E.separator(string=app_name, **attrs))
                    left_group, right_group = [], []
                    attrs['attrs'] = user_type_readonly
                    # we can't use enumerate, as we sometime skip groups
                    group_count = 0
                    for g in gs:
                        field_name = name_boolean_group(g.id)
                        dest_group = left_group if group_count % 2 == 0 else right_group
                        if g == group_no_one:
                            # make the group_no_one invisible in the form view
                            dest_group.append(E.field(name=field_name, invisible="1", **attrs))
                        else:
                            dest_group.append(E.field(name=field_name, **attrs))
                        # add duplicate invisible field so default values are saved on create
                        xml0.append(E.field(name=field_name, **dict(attrs, invisible="1", groups='!base.group_no_one')))
                        group_count += 1
                    xml4.append(E.group(*left_group))
                    xml4.append(E.group(*right_group))

            xml4.append({'class': "o_label_nowrap"})
            if user_type_field_name:
                user_type_attrs = {'invisible': [(user_type_field_name, '!=', group_employee.id)]}
            else:
                user_type_attrs = {}

            for xml_cat in sorted(xml_by_category.keys(), key=lambda it: it[0]):
                master_category_name = xml_cat[1]
                xml3.append(E.group(*(xml_by_category[xml_cat]), string=master_category_name))

            field_name = 'user_group_warning'
            user_group_warning_xml = E.div({
                'class': "alert alert-warning",
                'role': "alert",
                'colspan': "2",
                'attrs': str({'invisible': [(field_name, '=', False)]})
            })
            user_group_warning_xml.append(E.label({
                'for': field_name,
                'string': "Access Rights Mismatch",
                'class': "text text-warning fw-bold",
            }))
            user_group_warning_xml.append(E.field(name=field_name))
            xml2.append(user_group_warning_xml)

            xml = E.field(
                *(xml0),
                E.group(*(xml1), groups="base.group_no_one"),
                E.group(*(xml2), attrs=str(user_type_attrs)),
                E.group(*(xml3), attrs=str(user_type_attrs)),
                E.group(*(xml4), attrs=str(user_type_attrs), groups="base.group_no_one"), name="groups_id", position="replace")
            xml.addprevious(etree.Comment("GENERATED AUTOMATICALLY BY GROUPS"))

        # serialize and update the view
        xml_content = etree.tostring(xml, pretty_print=True, encoding="unicode")
        if xml_content != view.arch:  # avoid useless xml validation if no change
            new_context = dict(view._context)
            new_context.pop('install_filename', None)  # don't set arch_fs for this computed view
            new_context['lang'] = None
            view.with_context(new_context).write({'arch': xml_content})

    def get_application_groups(self, domain):
        """ Return the non-share groups that satisfy ``domain``. """
        return self.search(domain + [('share', '=', False)])

    @api.model
    def get_groups_by_application(self):
        """ Return all groups classified by application (module category), as a list::

                [(app, kind, groups), ...],

            where ``app`` and ``groups`` are recordsets, and ``kind`` is either
            ``'boolean'`` or ``'selection'``. Applications are given in sequence
            order.  If ``kind`` is ``'selection'``, ``groups`` are given in
            reverse implication order.
        """
        def linearize(app, gs, category_name):
            # 'User Type' is an exception
            if app.xml_id == 'base.module_category_user_type':
                return (app, 'selection', gs.sorted('id'), category_name)
            # determine sequence order: a group appears after its implied groups
            order = {g: len(g.trans_implied_ids & gs) for g in gs}
            # We want a selection for Accounting too. Auditor and Invoice are both
            # children of Accountant, but the two of them make a full accountant
            # so it makes no sense to have checkboxes.
            if app.xml_id == 'base.module_category_accounting_accounting':
                return (app, 'selection', gs.sorted(key=order.get), category_name)
            # check whether order is total, i.e., sequence orders are distinct
            if len(set(order.values())) == len(gs):
                return (app, 'selection', gs.sorted(key=order.get), category_name)
            else:
                return (app, 'boolean', gs, (100, 'Other'))

        # classify all groups by application
        by_app, others = defaultdict(self.browse), self.browse()
        for g in self.get_application_groups([]):
            if g.category_id:
                by_app[g.category_id] += g
            else:
                others += g
        # build the result
        res = []
        for app, gs in sorted(by_app.items(), key=lambda it: it[0].sequence or 0):
            if app.parent_id:
                res.append(linearize(app, gs, (app.parent_id.sequence, app.parent_id.name)))
            else:
                res.append(linearize(app, gs, (100, 'Other')))

        if others:
            res.append((self.env['ir.module.category'], 'boolean', others, (100,'Other')))
        return res


class ModuleCategory(models.Model):
    _inherit = "ir.module.category"

    def write(self, values):
        res = super().write(values)
        if "name" in values:
            self.env["res.groups"]._update_user_groups_view()
        return res

    def unlink(self):
        res = super().unlink()
        self.env["res.groups"]._update_user_groups_view()
        return res


class UsersView(models.Model):
    _inherit = 'res.users'

    user_group_warning = fields.Text(string="User Group Warning", compute="_compute_user_group_warning")

    @api.depends('groups_id', 'share')
    @api.depends_context('show_user_group_warning')
    def _compute_user_group_warning(self):
        self.user_group_warning = False
        if self._context.get('show_user_group_warning'):
            for user in self.filtered_domain([('share', '=', False)]):
                group_inheritance_warnings = self._prepare_warning_for_group_inheritance(user)
                if group_inheritance_warnings:
                    user.user_group_warning = group_inheritance_warnings

    @api.model_create_multi
    def create(self, vals_list):
        new_vals_list = []
        for values in vals_list:
            new_vals_list.append(self._remove_reified_groups(values))
        users = super(UsersView, self).create(new_vals_list)
        group_multi_company_id = self.env['ir.model.data']._xmlid_to_res_id(
            'base.group_multi_company', raise_if_not_found=False)
        if group_multi_company_id:
            for user in users:
                if len(user.company_ids) <= 1 and group_multi_company_id in user.groups_id.ids:
                    user.write({'groups_id': [Command.unlink(group_multi_company_id)]})
                elif len(user.company_ids) > 1 and group_multi_company_id not in user.groups_id.ids:
                    user.write({'groups_id': [Command.link(group_multi_company_id)]})
        return users

    def write(self, values):
        values = self._remove_reified_groups(values)
        res = super(UsersView, self).write(values)
        if 'company_ids' not in values:
            return res
        group_multi_company = self.env.ref('base.group_multi_company', False)
        if group_multi_company:
            for user in self:
                if len(user.company_ids) <= 1 and user.id in group_multi_company.users.ids:
                    user.write({'groups_id': [Command.unlink(group_multi_company.id)]})
                elif len(user.company_ids) > 1 and user.id not in group_multi_company.users.ids:
                    user.write({'groups_id': [Command.link(group_multi_company.id)]})
        return res

    @api.model
    def new(self, values=None, origin=None, ref=None):
        if values is None:
            values = {}
        values = self._remove_reified_groups(values)
        user = super().new(values=values, origin=origin, ref=ref)
        group_multi_company = self.env.ref('base.group_multi_company', False)
        if group_multi_company and 'company_ids' in values:
            if len(user.company_ids) <= 1 and user.id in group_multi_company.users.ids:
                user.update({'groups_id': [Command.unlink(group_multi_company.id)]})
            elif len(user.company_ids) > 1 and user.id not in group_multi_company.users.ids:
                user.update({'groups_id': [Command.link(group_multi_company.id)]})
        return user

    def _prepare_warning_for_group_inheritance(self, user):
        """ Check (updated) groups configuration for user. If implieds groups
        will be added back due to inheritance and hierarchy in groups return
        a message explaining the missing groups.

        :param res.users user: target user

        :return: string to display in a warning
        """
        # Current groups of the user
        current_groups = user.groups_id.filtered('trans_implied_ids')
        current_groups_by_category = defaultdict(lambda: self.env['res.groups'])
        for group in current_groups:
            current_groups_by_category[group.category_id] |= group.trans_implied_ids.filtered(lambda grp: grp.category_id == group.category_id)

        missing_groups = {}
        # We don't want to show warning for "Technical" and "Extra Rights" groups
        categories_to_ignore = self.env.ref('base.module_category_hidden') + self.env.ref('base.module_category_usability')
        for group in current_groups:
            # Get the updated group from current groups
            missing_implied_groups = group.implied_ids - user.groups_id
            # Get the missing group needed in updated group's category (For example, someone changes
            # Sales: Admin to Sales: User, but Field Service is already set to Admin, so here in the
            # 'Sales' category, we will at the minimum need Admin group)
            missing_implied_groups = missing_implied_groups.filtered(
                lambda g:
                g.category_id not in (group.category_id | categories_to_ignore) and
                g not in current_groups_by_category[g.category_id] and
                (self.user_has_groups('base.group_no_one') or g.category_id)
            )
            if missing_implied_groups:
                # prepare missing group message, by categories
                missing_groups[group] = ", ".join(f'"{missing_group.category_id.name or _("Other")}: {missing_group.name}"'
                                                  for missing_group in missing_implied_groups)
        return "\n".join(
            _('Since %(user)s is a/an "%(category)s: %(group)s", they will at least obtain the right %(missing_group_message)s',
              user=user.name,
              category=group.category_id.name or _('Other'),
              group=group.name,
              missing_group_message=missing_group_message
             ) for group, missing_group_message in missing_groups.items()
        )

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
            added = self.env['res.groups'].sudo().browse(add)
            added |= added.mapped('trans_implied_ids')
            added_ids = added._ids
            # remove group ids in `rem` and add group ids in `add`
            # do not remove groups that are added by implied
            values1['groups_id'] = list(itertools.chain(
                zip(repeat(3), [gid for gid in rem if gid not in added_ids]),
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

    def onchange(self, values, field_name, field_onchange):
        # field_name can be either a string, a list or Falsy
        if isinstance(field_name, list):
            names = field_name
        elif field_name:
            names = [field_name]
        else:
            names = []

        if any(is_reified_group(field) for field in names):
            field_name = (
                ['groups_id']
                + [field for field in names if not is_reified_group(field)]
            )
            values.pop('groups_id', None)
            values.update(self._remove_reified_groups(values))

        field_onchange['groups_id'] = ''
        result = super().onchange(values, field_name, field_onchange)
        if not field_name: # merged default_get
            self._add_reified_groups(
                filter(is_reified_group, field_onchange),
                result.setdefault('value', {})
            )
        return result

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

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if fields:
            # ignore reified fields
            fields = [fname for fname in fields if not is_reified_group(fname)]
        return super().read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

    def _add_reified_groups(self, fields, values):
        """ add the given reified group fields into `values` """
        gids = set(parse_m2m(values.get('groups_id') or []))
        for f in fields:
            if is_boolean_group(f):
                values[f] = get_boolean_group(f) in gids
            elif is_selection_groups(f):
                # determine selection groups, in order
                sel_groups = self.env['res.groups'].sudo().browse(get_selection_groups(f))
                sel_order = {g: len(g.trans_implied_ids & sel_groups) for g in sel_groups}
                sel_groups = sel_groups.sorted(key=sel_order.get)
                # determine which ones are in gids
                selected = [gid for gid in sel_groups.ids if gid in gids]
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
                tips = []
                if app.description:
                    tips.append(app.description + '\n')
                tips.extend('%s: %s' % (g.name, g.comment) for g in gs if g.comment)
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
        # add self readable/writable fields
        missing = set(self.SELF_WRITEABLE_FIELDS).union(self.SELF_READABLE_FIELDS).difference(res.keys())
        if allfields:
            missing = missing.intersection(allfields)
        if missing:
            res.update({
                key: dict(values, readonly=key not in self.SELF_WRITEABLE_FIELDS, searchable=False)
                for key, values in super(UsersView, self.sudo()).fields_get(missing, attributes).items()
            })
        return res

class CheckIdentity(models.TransientModel):
    """ Wizard used to re-check the user's credentials (password)

    Might be useful before the more security-sensitive operations, users might be
    leaving their computer unlocked & unattended. Re-checking credentials mitigates
    some of the risk of a third party using such an unattended device to manipulate
    the account.
    """
    _name = 'res.users.identitycheck'
    _description = "Password Check Wizard"

    request = fields.Char(readonly=True, groups=fields.NO_ACCESS)
    password = fields.Char()

    def run_check(self):
        assert request, "This method can only be accessed over HTTP"
        try:
            self.create_uid._check_credentials(self.password, {'interactive': True})
        except AccessDenied:
            raise UserError(_("Incorrect Password, try again or click on Forgot Password to reset your password."))
        finally:
            self.password = False

        request.session['identity-check-last'] = time.time()
        ctx, model, ids, method = json.loads(self.sudo().request)
        method = getattr(self.env(context=ctx)[model].browse(ids), method)
        assert getattr(method, '__has_check_identity', False)
        return method()

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
            if not line.new_passwd:
                raise UserError(_("Before clicking on 'Change Password', you have to write a new password."))
            line.user_id._change_password(line.new_passwd)
        # don't keep temporary passwords in the database longer than necessary
        self.write({'new_passwd': False})

class ChangePasswordOwn(models.TransientModel):
    _name = "change.password.own"
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
class APIKeysUser(models.Model):
    _inherit = 'res.users'

    api_key_ids = fields.One2many('res.users.apikeys', 'user_id', string="API Keys")

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ['api_key_ids']

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + ['api_key_ids']

    def _rpc_api_keys_only(self):
        """ To be overridden if RPC access needs to be restricted to API keys, e.g. for 2FA """
        return False

    def _check_credentials(self, password, user_agent_env):
        user_agent_env = user_agent_env or {}
        if user_agent_env.get('interactive', True):
            if 'interactive' not in user_agent_env:
                _logger.warning(
                    "_check_credentials without 'interactive' env key, assuming interactive login. \
                    Check calls and overrides to ensure the 'interactive' key is properly set in \
                    all _check_credentials environments"
                )
            return super()._check_credentials(password, user_agent_env)

        if not self.env.user._rpc_api_keys_only():
            try:
                return super()._check_credentials(password, user_agent_env)
            except AccessDenied:
                pass

        # 'rpc' scope does not really exist, we basically require a global key (scope NULL)
        if self.env['res.users.apikeys']._check_credentials(scope='rpc', key=password) == self.env.uid:
            return

        raise AccessDenied()

    @check_identity
    def api_key_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'res.users.apikeys.description',
            'name': 'New API Key',
            'target': 'new',
            'views': [(False, 'form')],
        }

class APIKeys(models.Model):
    _name = 'res.users.apikeys'
    _description = 'Users API Keys'
    _auto = False # so we can have a secret column
    _allow_sudo_commands = False

    name = fields.Char("Description", required=True, readonly=True)
    user_id = fields.Many2one('res.users', index=True, required=True, readonly=True, ondelete="cascade")
    scope = fields.Char("Scope", readonly=True)
    create_date = fields.Datetime("Creation Date", readonly=True)

    def init(self):
        table = sql.Identifier(self._table)
        self.env.cr.execute(sql.SQL("""
        CREATE TABLE IF NOT EXISTS {table} (
            id serial primary key,
            name varchar not null,
            user_id integer not null REFERENCES res_users(id),
            scope varchar,
            index varchar({index_size}) not null CHECK (char_length(index) = {index_size}),
            key varchar not null,
            create_date timestamp without time zone DEFAULT (now() at time zone 'utc')
        )
        """).format(table=table, index_size=sql.Placeholder('index_size')), {
            'index_size': INDEX_SIZE
        })

        index_name = self._table + "_user_id_index_idx"
        if len(index_name) > 63:
            # unique determinist index name
            index_name = self._table[:50] + "_idx_" + sha256(self._table.encode()).hexdigest()[:8]
        self.env.cr.execute(sql.SQL("""
        CREATE INDEX IF NOT EXISTS {index_name} ON {table} (user_id, index);
        """).format(
            table=table,
            index_name=sql.Identifier(index_name)
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
            return {'type': 'ir.actions.act_window_close'}
        raise AccessError(_("You can not remove API keys unless they're yours or you are a system user"))

    def _check_credentials(self, *, scope, key):
        assert scope, "scope is required"
        index = key[:INDEX_SIZE]
        self.env.cr.execute('''
            SELECT user_id, key
            FROM {} INNER JOIN res_users u ON (u.id = user_id)
            WHERE u.active and index = %s AND (scope IS NULL OR scope = %s)
        '''.format(self._table),
        [index, scope])
        for user_id, current_key in self.env.cr.fetchall():
            if KEY_CRYPT_CONTEXT.verify(key, current_key):
                return user_id

    def _generate(self, scope, name):
        """Generates an api key.
        :param str scope: the scope of the key. If None, the key will give access to any rpc.
        :param str name: the name of the key, mainly intended to be displayed in the UI.
        :return: str: the key.

        """
        # no need to clear the LRU when *adding* a key, only when removing
        k = binascii.hexlify(os.urandom(API_KEY_SIZE)).decode()
        self.env.cr.execute("""
        INSERT INTO {table} (name, user_id, scope, key, index)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
        """.format(table=self._table),
        [name, self.env.user.id, scope, KEY_CRYPT_CONTEXT.hash(k), k[:INDEX_SIZE]])

        ip = request.httprequest.environ['REMOTE_ADDR'] if request else 'n/a'
        _logger.info("%s generated: scope: <%s> for '%s' (#%s) from %s",
            self._description, scope, self.env.user.login, self.env.uid, ip)

        return k

class APIKeyDescription(models.TransientModel):
    _name = 'res.users.apikeys.description'
    _description = 'API Key Description'

    name = fields.Char("Description", required=True)

    @check_identity
    def make_key(self):
        # only create keys for users who can delete their keys
        self.check_access_make_key()

        description = self.sudo()
        k = self.env['res.users.apikeys']._generate(None, self.sudo().name)
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
        if not self.user_has_groups('base.group_user'):
            raise AccessError(_("Only internal users can create API keys"))

class APIKeyShow(models.AbstractModel):
    _name = 'res.users.apikeys.show'
    _description = 'Show API Key'

    # the field 'id' is necessary for the onchange that returns the value of 'key'
    id = fields.Id()
    key = fields.Char(readonly=True)
