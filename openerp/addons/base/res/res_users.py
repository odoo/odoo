# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import uuid

from collections import defaultdict
from datetime import datetime, timedelta
from itertools import chain, repeat
from lxml import etree
from lxml.builder import E
from passlib.context import CryptContext
from psycopg2 import OperationalError

from odoo import api, fields, models, tools, SUPERUSER_ID, _
from odoo.exceptions import AccessDenied, AccessError, UserError, ValidationError
from odoo.osv import expression
from odoo.service.db import check_super
from odoo.tools import partition

_logger = logging.getLogger(__name__)

default_crypt_context = CryptContext(
    # kdf which can be verified by the context. The default encryption kdf is
    # the first of the list
    ['pbkdf2_sha512', 'md5_crypt', 'plaintext'],
    # deprecated algorithms are still verified as usual, but ``needs_update``
    # will indicate that the stored hash should be replaced by a more recent
    # algorithm. Passlib 1.6 supports an `auto` value which deprecates any
    # algorithm but the default, but Ubuntu LTS only provides 1.5 so far.
    deprecated=['md5_crypt', 'plaintext'],
)

# Only users who can modify the user (incl. the user herself) see the real contents of these fields
USER_PRIVATE_FIELDS = ['password']

concat = chain.from_iterable

#
# Functions for manipulating boolean and selection pseudo-fields
#
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
        for group, group1 in zip(self, self.sudo()):
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

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        # add explicit ordering if search is sorted on full_name
        if order and order.startswith('full_name'):
            groups = super(Groups, self).search(args)
            groups = groups.sorted('full_name', reverse=order.endswith('DESC'))
            groups = groups[offset:offset+limit] if limit else groups[offset:]
            return len(groups) if count else groups.ids
        return super(Groups, self).search(args, offset=offset, limit=limit, order=order, count=count)

    @api.multi
    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {}, name=_('%s (copy)') % self.name)
        return super(Groups, self).copy(default)

    @api.multi
    def write(self, vals):
        if 'name' in vals:
            if vals['name'].startswith('-'):
                raise UserError(_('The name of the group can not start with "-"'))
        res = super(Groups, self).write(vals)
        self.env['ir.model.access'].call_cache_clearing_methods()
        self.env['res.users'].has_group.clear_cache(self.env['res.users'])
        return res


class ResUsersLog(models.Model):
    _name = 'res.users.log'
    _order = 'id desc'
    # Currenly only uses the magical fields: create_uid, create_date,
    # for recording logins. To be extended for other uses (chat presence, etc.)
    token_id = fields.Many2one('res.users.token', string='Token used', readonly=True, ondelete='set null')


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

    # User can write on a few of his own fields (but not his groups for example)
    SELF_WRITEABLE_FIELDS = ['signature', 'action_id', 'company_id', 'email', 'name', 'image', 'image_medium', 'image_small', 'lang', 'tz']
    # User can read a few of his own fields
    SELF_READABLE_FIELDS = ['signature', 'company_id', 'login', 'email', 'name', 'image', 'image_medium', 'image_small', 'lang', 'tz', 'tz_offset', 'groups_id', 'partner_id', '__last_update', 'action_id']

    def __init__(self, pool, cr):
        super(Users, self).__init__(pool, cr)
        try:
            # hasattr with name mangling
            pool.__uid_cache
        except AttributeError:
            pool.__uid_cache = defaultdict(dict)  # {uid: {password: {}, token: {}}}

    def clear_caches(self):
        self.pool.__uid_cache = defaultdict(dict)
        return super(Users, self).clear_caches()

    def _default_groups(self):
        default_user = self.env.ref('base.default_user', raise_if_not_found=False)
        return (default_user or self.env['res.users']).groups_id

    def _companies_count(self):
        return self.env['res.company'].sudo().search_count([])

    @api.one
    @api.depends('token_ids')
    def _get_password(self):
        self.password = ''

    @api.multi
    def _set_password(self):
        if self.env.uid == SUPERUSER_ID:
            for user in self:
                token = self.env['res.users.token'].search([('user_id', '=', user.id), ('type', '=', 'password')])
                if token:
                    token.write({'token': user.password})
                if not token and user.password:
                    token = token.create({
                        'user_id': user.id,
                        'type': 'password',
                        'token': user.password,
                    })

    partner_id = fields.Many2one('res.partner', required=True, ondelete='restrict', auto_join=True,
        string='Related Partner', help='Partner-related data of the user')
    login = fields.Char(required=True, help="Used to log into the system")
    password = fields.Char(compute='_get_password', inverse='_set_password', invisible=True, copy=False,
        help="Keep empty if you don't want the user to be able to connect on the system.")
    # The below `token_ids` field is set for tehnical reasons, for the @api.depends of the compute method.
    # The compute method is supposed to always return an empty string
    # But without this @api.depends, the password field actually contains the password when browsing the user
    # directly after creation.
    token_ids = fields.One2many('res.users.token', 'user_id', string="Tokens")
    api_token_ids = fields.One2many('res.users.token', 'user_id', string="API Keys", domain=[('type', '=', 'apikey')])
    signature = fields.Html()
    active = fields.Boolean(default=True)
    action_id = fields.Many2one('ir.actions.actions', string='Home Action',
        help="If specified, this action will be opened at log on for this user, in addition to the standard menu.")
    groups_id = fields.Many2many('res.groups', 'res_groups_users_rel', 'uid', 'gid', string='Groups', default=_default_groups)
    log_ids = fields.One2many('res.users.log', 'create_uid', string='User log entries')
    login_date = fields.Datetime(related='log_ids.create_date', string='Latest connection')
    share = fields.Boolean(compute='_compute_share', string='Share User', store=True,
         help="External user with limited access, created only for the purpose of sharing data.")
    companies_count = fields.Integer(compute='_compute_companies_count', string="Number of Companies", default=_companies_count)
    
    @api.v7
    def _get_company(self, cr, uid, context=None, uid2=False):
        user = self.browse(cr, uid, uid2 or uid, context=context)
        return Users._get_company(user).id

    @api.v8
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

    _sql_constraints = [
        ('login_key', 'UNIQUE (login)',  'You can not have two users with the same login !')
    ]

    @api.depends('groups_id')
    def _compute_share(self):
        for user in self:
            user.share = not user.has_group('base.group_user')

    @api.multi
    def _compute_companies_count(self):
        companies_count = self._companies_count()
        for user in self:
            user.companies_count = companies_count

    @api.onchange('login')
    def on_change_login(self):
        if self.login and tools.single_email_re.match(self.login):
            self.email = self.login

    @api.onchange('state_id')
    def onchange_state(self):
        return self.mapped('partner_id').onchange_state()

    @api.onchange('parent_id')
    def onchange_parent_id(self):
        return self.mapped('partner_id').onchange_parent_id()

    @api.multi
    @api.constrains('company_id', 'company_ids')
    def _check_company(self):
        if any(user.company_ids and user.company_id not in user.company_ids for user in self):
            raise ValidationError(_('The chosen company is not in the allowed companies for this user'))

    @api.v7
    def read(self, cr, uid, ids, fields=None, context=None, load='_classic_read'):
        result = Users.read(self.browse(cr, uid, ids, context), fields, load=load)
        return result if isinstance(ids, list) else (bool(result) and result[0])

    @api.v8
    def read(self, fields=None, load='_classic_read'):
        if fields and self == self.env.user:
            for key in fields:
                if not (key in self.SELF_READABLE_FIELDS or key.startswith('context_')):
                    break
            else:
                # safe fields only, so we read as super-user to bypass access rights
                self = self.sudo()

        result = super(Users, self).read(fields=fields, load=load)

        canwrite = self.env['ir.model.access'].check('res.users', 'write', False)
        if not canwrite:
            def override_password(vals):
                if (vals['id'] != self._uid):
                    for key in USER_PRIVATE_FIELDS:
                        if key in vals:
                            vals[key] = '********'
                return vals
            result = map(override_password, result)

        return result

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if self._uid != SUPERUSER_ID:
            groupby_fields = set([groupby] if isinstance(groupby, basestring) else groupby)
            if groupby_fields.intersection(USER_PRIVATE_FIELDS):
                raise AccessError(_('Invalid groupby'))
        return super(Users, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        if self._uid != SUPERUSER_ID and args:
            domain_fields = {term[0] for term in args if isinstance(term, (tuple, list))}
            if domain_fields.intersection(USER_PRIVATE_FIELDS):
                raise AccessError(_('Invalid search criterion'))
        return super(Users, self)._search(args, offset=offset, limit=limit, order=order, count=count,
                                          access_rights_uid=access_rights_uid)

    @api.model
    def create(self, vals):
        user = super(Users, self).create(vals)
        user.partner_id.active = user.active
        if user.partner_id.company_id:
            user.partner_id.write({'company_id': user.company_id.id})
        return user

    @api.multi
    def write(self, values):
        if values.get('active') == False:
            for user in self:
                if user.id == SUPERUSER_ID:
                    raise UserError(_("You cannot deactivate the admin user."))
                elif user.id == self._uid:
                    raise UserError(_("You cannot deactivate the user you're currently logged in as."))

        if self == self.env.user:
            for key in values.keys():
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
                if user.partner_id.company_id.id != values['company_id']:
                    user.partner_id.write({'company_id': user.company_id.id})
            # clear default ir values when company changes
            self.env['ir.values'].get_defaults_dict.clear_cache(self.env['ir.values'])
        # clear caches linked to the users
        self.env['ir.model.access'].call_cache_clearing_methods()
        self.env['ir.rule'].clear_caches()
        self.context_get.clear_cache(self)
        self.has_group.clear_cache(self)
        return res

    @api.multi
    def unlink(self):
        if SUPERUSER_ID in self.ids:
            raise UserError(_('You can not remove the admin user as it is used internally for resources created by Odoo (updates, module installation, ...)'))
        return super(Users, self).unlink()

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if args is None:
            args = []
        users = self.browse()
        if name and operator in ['=', 'ilike']:
            users = self.search([('login', '=', name)] + args, limit=limit)
        if not users:
            users = self.search([('name', operator, name)] + args, limit=limit)
        return users.name_get()

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
    def check_credentials(self, password):
        """ Override this method to plug additional authentication methods"""
        resUsersToken = self.env['res.users.token']
        for token_type, token_label in resUsersToken._get_type_selection():
            prefix_length = resUsersToken._get_type_prefix_length()[token_type]
            self.env.cr.execute("""
                SELECT id, hash
                FROM res_users_token
                WHERE
                    user_id=%s AND
                    type=%s AND
                    prefix=%s AND
                    (expiry_date IS NULL or expiry_date >= %s)
            """, (self.env.uid, token_type, password[:prefix_length], fields.Datetime.now()))
            for token_id, token_hash in self.env.cr.fetchall():
                token = resUsersToken.sudo().browse(token_id)
                match, replacement = token._crypt_context().verify_and_update(password, token_hash)
                if replacement is not None and not self.env.registry.in_test_mode:
                    try:
                        token._set_encrypted_token(replacement)
                    except OperationalError:
                        # It doesn't matter if the replacement token can't be set because of a concurrent update.
                        # It will be done later.
                        pass
                    except Exception:
                        # The inability to set the replacement token should not prevent the user to sign in,
                        # but should be referenced in the logs as an exception for the administrator to be aware of it.
                        _logger.exception(_('Error when attempting to set replacement token'))
                        pass
                if match and token.validate(password):
                    return token
        else:
            raise AccessDenied()

    @api.model
    def _update_last_login(self, token_id=None):
        # only create new records to avoid any side-effect on concurrent transactions
        # extra records will be deleted by the periodical garbage collection
        self.env['res.users.log'].create({'token_id': token_id})  # `create_uid` populated by defaults

    def _login(self, db, login, password):
        if not password:
            return False
        user_id = False
        try:
            with self.pool.cursor() as cr:
                res = self.search(cr, SUPERUSER_ID, [('login','=',login)])
                if res:
                    user_id = res[0]
                    token = self.check_credentials(cr, user_id, password)
                    self._update_last_login(cr, user_id, token_id=token.id)
        except AccessDenied:
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
        if uid == SUPERUSER_ID:
            # Successfully logged in as admin!
            # Attempt to guess the web base url...
            if user_agent_env and user_agent_env.get('base_location'):
                try:
                    with self.pool.cursor() as cr:
                        base = user_agent_env['base_location']
                        ICP = self.pool['ir.config_parameter']
                        if not ICP.get_param(cr, uid, 'web.base.url.freeze'):
                            ICP.set_param(cr, uid, 'web.base.url', base)
                except Exception:
                    _logger.exception("Failed to update web.base.url configuration parameter")
        return uid

    def check(self, db, uid, passwd):
        """Verifies that the given (uid, password) is authorized for the database ``db`` and
           raise an exception if it is not."""
        if not passwd:
            # empty passwords disallowed for obvious security reasons
            raise AccessDenied()
        if passwd in self.pool.__uid_cache[uid]:
            if self._check_uid_cache_values(passwd, self.pool.__uid_cache[uid][passwd]):
                return
            else:
                self.pool.__uid_cache[uid].pop(passwd)
        cr = self.pool.cursor()
        try:
            token = self.check_credentials(cr, uid, passwd)
            cache_values = self._prepare_uid_cache_values(cr, uid, passwd, token)
            self.pool.__uid_cache[uid].update({passwd: cache_values})
        finally:
            cr.close()

    @api.model
    def _prepare_uid_cache_values(self, passwd, token):
        return {'expiry_date': token.expiry_date}

    def _check_uid_cache_values(self, passwd, cached_values):
        expiry_date = cached_values.get('expiry_date') or None
        if expiry_date:
            expiry_date = datetime.strptime(expiry_date, tools.DEFAULT_SERVER_DATETIME_FORMAT)
            now = datetime.strptime(fields.Datetime.now(), tools.DEFAULT_SERVER_DATETIME_FORMAT)
            if expiry_date < now:
                return False
        return True

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

    @api.v7
    def has_group(self, cr, uid, group_ext_id):
        return self._has_group(cr, uid, group_ext_id)

    @api.v8
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
    def _is_admin(self):
        self.ensure_one()
        return self.id == SUPERUSER_ID or self.has_group('base.group_erp_manager')

    @api.model
    def get_company_currency_id(self):
        return self.env.user.company_id.currency_id.id


class UsersToken(models.Model):
    _name = "res.users.token"
    _order = "id desc"

    def init(self):
        self.env.cr.execute("""
            DO $$
                BEGIN
                    ALTER TABLE res_users_token ADD COLUMN hash varchar NOT NULL;
                EXCEPTION
                    WHEN duplicate_column THEN null;
                END;
            $$;
        """)

    @api.model
    def _get_type_selection(self):
        return [('password', 'Password'), ('apikey', 'API Key')]

    def _get_type_prefix_length(self):
        return defaultdict(lambda: 3, {'password': 0, 'apikey': 3})

    user_id = fields.Many2one('res.users', string='User', required=True, readonly=True, ondelete='cascade')
    token = fields.Char(compute='_get_token', inverse='_set_token', string='Token')
    prefix = fields.Char(string='Prefix', readonly=True, default='')
    expiry_date = fields.Datetime(string='Expiration date')
    type = fields.Selection('_get_type_selection', required=True, readonly=True)
    comment = fields.Text(string='Comment')

    def encrypt(self, token):
        return self._crypt_context().encrypt(token)

    @api.one
    @api.depends('prefix')
    def _get_token(self):
        self.token = self.prefix

    @api.multi
    def _set_token(self):
        for record in self:
            if self.token:
                token_prefix = self.token[:self._get_type_prefix_length()[self.type]]
                token_hash = self.encrypt(self.token)
                self.env.cr.execute("UPDATE res_users_token SET hash=%s, prefix=%s WHERE id = %s", (token_hash, token_prefix, record.id))
            elif record.type == 'password':
                record.unlink()
            else:
                raise UserError(_('You cannot set an access token without setting a token'))

    @api.multi
    def write(self, values):
        res = super(UsersToken, self).write(values)
        self.env['res.users'].clear_caches()
        return res

    @api.multi
    def unlink(self):
        res = super(UsersToken, self).unlink()
        self.env['res.users'].clear_caches()
        return res

    def _set_encrypted_token(self, encrypted):
        """ Store the provided encrypted password to the database, and clears
        any plaintext password
        """
        self.env.cr.execute(
            "UPDATE res_users_token SET hash=%s WHERE id=%s",
            (encrypted, self.id))

    def _crypt_context(self):
        """ Passlib CryptContext instance used to encrypt and verify
        passwords. Can be overridden if technical, legal or political matters
        require different kdfs than the provided default.

        Requires a CryptContext as deprecation and upgrade notices are used
        internally
        """
        return default_crypt_context

    @api.v8
    def validate(self, token):
        """ Return True or False if the token is valid or not (respectively).
            This method is meant to be overridden in addons that want
            to make their tokens validated on another concept than the
            expiration date.
        """
        self.ensure_one()
        return True

    @api.v7
    def validate(self, cr, uid, ids, token, context=None):
        return UsersToken.validate(self.browse(cr, uid, ids, context=context), token)


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

    @api.model
    def create(self, values):
        user_ids = values.pop('users', None)
        group = super(GroupsImplied, self).create(values)
        if user_ids:
            # delegate addition of users to add implied groups
            group.write({'users': user_ids})
        return group

    @api.multi
    def write(self, values):
        res = super(GroupsImplied, self).write(values)
        if values.get('users') or values.get('implied_ids'):
            # add all implied groups (to all users of each group)
            for group in self:
                vals = {'users': zip(repeat(4), group.users.ids)}
                super(GroupsImplied, group.trans_implied_ids).write(vals)
        return res


class UsersImplied(models.Model):
    _inherit = 'res.users'

    @api.model
    def create(self, values):
        groups = values.pop('groups_id', None)
        user = super(UsersImplied, self).create(values)
        if groups:
            # delegate addition of groups to add implied groups
            user.write({'groups_id': groups})
            self.env['ir.ui.view'].clear_caches()
        return user

    @api.multi
    def write(self, values):
        res = super(UsersImplied, self).write(values)
        if values.get('groups_id'):
            # add implied groups for all users
            for user in self.with_context({}):
                gs = set(concat(g.trans_implied_ids for g in user.groups_id))
                vals = {'groups_id': [(4, g.id) for g in gs]}
                super(UsersImplied, self).write(vals)
            self.env['ir.ui.view'].clear_caches()
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

    @api.model
    def create(self, values):
        user = super(GroupsView, self).create(values)
        self._update_user_groups_view()
        # ir_values.get_actions() depends on action records
        self.env['ir.values'].clear_caches()
        return user

    @api.multi
    def write(self, values):
        res = super(GroupsView, self).write(values)
        if 'category_id' in values:
            self._update_user_groups_view()
        # ir_values.get_actions() depends on action records
        self.env['ir.values'].clear_caches()
        return res

    @api.multi
    def unlink(self):
        res = super(GroupsView, self).unlink()
        self._update_user_groups_view()
        # ir_values.get_actions() depends on action records
        self.env['ir.values'].clear_caches()
        return res

    @api.model
    def _update_user_groups_view(self):
        """ Modify the view with xmlid ``base.user_groups_view``, which inherits
            the user form view, and introduces the reified group fields.
        """
        if self._context.get('install_mode'):
            # use installation/admin language for translatable names in the view
            user_context = self.env['res.users'].context_get()
            self = self.with_context(**user_context)

        # We have to try-catch this, because at first init the view does not
        # exist but we are already creating some basic groups.
        view = self.env.ref('base.user_groups_view', raise_if_not_found=False)
        if view and view.exists() and view._name == 'ir.ui.view':
            group_no_one = view.env.ref('base.group_no_one')
            xml1, xml2 = [], []
            xml1.append(E.separator(string=_('Application'), colspan="2"))
            for app, kind, gs in self.get_groups_by_application():
                # hide groups in categories 'Hidden' and 'Extra' (except for group_no_one)
                attrs = {}
                if app.xml_id in ('base.module_category_hidden', 'base.module_category_extra', 'base.module_category_usability'):
                    attrs['groups'] = 'base.group_no_one'

                if kind == 'selection':
                    # application name with a selection field
                    field_name = name_selection_groups(gs.ids)
                    xml1.append(E.field(name=field_name, **attrs))
                    xml1.append(E.newline())
                else:
                    # application separator with boolean fields
                    app_name = app.name or _('Other')
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
            view.with_context(lang=None).write({'arch': xml_content})

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
        def linearize(app, gs):
            # determine sequence order: a group appears after its implied groups
            order = {g: len(g.trans_implied_ids & gs) for g in gs}
            # check whether order is total, i.e., sequence orders are distinct
            if len(set(order.itervalues())) == len(gs):
                return (app, 'selection', gs.sorted(key=order.get))
            else:
                return (app, 'boolean', gs)

        # classify all groups by application
        by_app, others = defaultdict(self.browse), self.browse()
        for g in self.get_application_groups([]):
            if g.category_id:
                by_app[g.category_id] += g
            else:
                others += g
        # build the result
        res = []
        for app, gs in sorted(by_app.iteritems(), key=lambda (a, _): a.sequence or 0):
            res.append(linearize(app, gs))
        if others:
            res.append((self.env['ir.module.category'], 'boolean', others))
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
                group_multi_company.write({'users': [(3, user.id)]})
            elif len(user.company_ids) > 1 and user.id not in group_multi_company.users.ids:
                group_multi_company.write({'users': [(4, user.id)]})
        return user

    @api.multi
    def write(self, values):
        values = self._remove_reified_groups(values)
        res = super(UsersView, self).write(values)
        group_multi_company = self.env.ref('base.group_multi_company', False)
        if group_multi_company and 'company_ids' in values:
            for user in self:
                if len(user.company_ids) <= 1 and user.id in group_multi_company.users.ids:
                    group_multi_company.write({'users': [(3, user.id)]})
                elif len(user.company_ids) > 1 and user.id not in group_multi_company.users.ids:
                    group_multi_company.write({'users': [(4, user.id)]})
        return res

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

    @api.model
    def default_get(self, fields):
        group_fields, fields = partition(is_reified_group, fields)
        fields1 = (fields + ['groups_id']) if group_fields else fields
        values = super(UsersView, self).default_get(fields1)
        self._add_reified_groups(group_fields, values)
        return values

    @api.v7
    def read(self, cr, uid, ids, fields=None, context=None, load='_classic_read'):
        result = UsersView.read(self.browse(cr, uid, ids, context), fields, load=load)
        return result if isinstance(ids, list) else (bool(result) and result[0])

    @api.v8
    def read(self, fields=None, load='_classic_read'):
        # determine whether reified groups fields are required, and which ones
        fields1 = fields or self.fields_get().keys()
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
                values[f] = selected and selected[-1] or False

    @api.model
    def fields_get(self, allfields=None, write_access=True, attributes=None):
        res = super(UsersView, self).fields_get(allfields=allfields, write_access=write_access, attributes=attributes)
        # add reified groups fields
        if not self.env.user._is_admin():
            return res
        for app, kind, gs in self.env['res.groups'].sudo().get_groups_by_application():
            if kind == 'selection':
                # selection group field
                tips = ['%s: %s' % (g.name, g.comment) for g in gs if g.comment]
                res[name_selection_groups(gs.ids)] = {
                    'type': 'selection',
                    'string': app.name or _('Other'),
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

    wizard_id = fields.Many2one('change.password.wizard', string='Wizard', required=True)
    user_id = fields.Many2one('res.users', string='User', required=True, ondelete='cascade')
    user_login = fields.Char(string='User Login', readonly=True)
    new_passwd = fields.Char(string='New Password', default='')

    @api.multi
    def change_password_button(self):
        for line in self:
            line.user_id.write({'password': line.new_passwd})
        # don't keep temporary passwords in the database longer than necessary
        self.write({'new_passwd': False})


class CreateAPIKey(models.TransientModel):
    _name = "res.users.api_key.create"

    user_id = fields.Many2one('res.users', string='User', required=True, ondelete='cascade')
    expiry_date = fields.Datetime('Expiration date', default=lambda self: (fields.Datetime.from_string(fields.Datetime.now()) + timedelta(days=180)).strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT))
    comment = fields.Text(string='Comment')
    api_key = fields.Char(string="API Key", compute="_get_api_key")

    @api.one
    def _get_api_key(self):
        self.api_key = self.env.context.get('api_key')

    @api.multi
    def apply(self):
        self.ensure_one()
        api_key = str(uuid.uuid4())
        self.env['res.users.token'].create({
            'user_id': self.user_id.id,
            'token': api_key,
            'expiry_date': self.expiry_date,
            'type': 'apikey',
            'comment': self.comment,
        })
        view_id = self.env['ir.model.data'].xmlid_to_res_id('base.res_users_api_key_create_view')
        return {
            'name': 'API Key created',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id,
            'res_model': 'res.users.api_key.create',
            'type': 'ir.actions.act_window',
            'res_id': self.id,
            'context': dict(self.env.context, api_key=api_key),
            'target': 'new',
        }
