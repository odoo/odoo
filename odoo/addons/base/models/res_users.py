import collections
import contextlib
import datetime
import ipaddress
import logging
import time
import uuid
from functools import wraps
from hashlib import sha256
from typing import TYPE_CHECKING, Any, Self

from lxml import etree
from markupsafe import Markup

from odoo import _, api, fields, models, tools
from odoo.api import SUPERUSER_ID, DomainType, ValuesType
from odoo.db import schema as sql
from odoo.exceptions import (
    AccessDenied,
    AccessError,
    UserError,
    ValidationError,
)
from odoo.fields import Command, Domain
from odoo.http import DEFAULT_LANG, request
from odoo.libs.datetime import all_timezones
from odoo.libs.debug_log import DebugLog
from odoo.libs.json import dumps as json_dumps
from odoo.libs.password import CryptContext
from odoo.tools import (
    SQL,
    email_domain_extract,
    frozendict,
    is_html_empty,
    reset_cached_properties,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Generator
from .res_users_auth import PasswordStore, session_token
from .res_users_login_cooldown import LoginCooldown

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


_DUMMY_PASSWORD_HASH = (
    "$pbkdf2-sha512$600000$7w4wftbyNcmfyucdH94fxA$"
    "6gY5uDHtaWIcyKdWlT0sfnF8OhSZMjbKmB8DizAUKVRJ8HidOesEczP4wP5dSBKAZPAuoE2TuABEWSXm6XGR1Q"
)

DEBUG_GROUP = "base.group_no_one"

_UNRESOLVED_GROUPS_WARNED: set[str] = set()

_RELATION_ONLY_COMMANDS = frozenset(
    {Command.UNLINK, Command.LINK, Command.CLEAR, Command.SET}
)


def _is_private_address(source: str | None) -> bool:
    try:
        return ipaddress.ip_address(source).is_private
    except ValueError:
        return False


def _is_jsonable(o: object) -> bool:
    try:
        json_dumps(o)
    except TypeError:
        return False
    else:
        return True


def check_identity(
    fn: Callable[..., dict[str, Any]],
) -> Callable[..., dict[str, Any]]:

    @wraps(fn)
    def wrapped(self: ResUsers, *args: Any, **kwargs: Any) -> dict[str, Any]:
        if not request:
            raise UserError(_("This method can only be accessed over HTTP"))

        if request.session.get("identity-check-last", 0) > time.time() - 10 * 60:
            _debug.logic("identity_check_recent", uid=self.env.uid, method=fn.__name__)
            return fn(self, *args, **kwargs)
        _debug.pipeline("identity_check_required", uid=self.env.uid, method=fn.__name__)

        w = (
            self.sudo()
            .env["res.users.identitycheck"]
            .create(
                {
                    "request": json_dumps(
                        [
                            {
                                k: v
                                for k, v in self.env.context.items()
                                if _is_jsonable(v)
                            },
                            self._name,
                            self.ids,
                            fn.__name__,
                            args,
                            kwargs,
                        ]
                    )
                }
            )
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": "res.users.identitycheck",
            "res_id": w.id,
            "name": _("Access Control"),
            "target": "new",
            "views": [(False, "form")],
            "context": {"dialog_size": "medium"},
        }

    wrapped.__has_check_identity = True
    return wrapped


class ResUsers(models.Model):
    _name = "res.users"
    _description = "User"
    _inherits = {"res.partner": "partner_id"}
    _order = "name, login"
    _display_name_column = "name"
    _display_name_context_keys = (
        "formatted_display_name",
        "crm_formatted_display_name_team",
    )
    _display_name_search_exact = ("login",)
    _allow_sudo_commands = False

    @property
    def SELF_READABLE_FIELDS(self) -> list[str]:
        return [
            "signature",
            "company_id",
            "login",
            "email",
            "name",
            "image_1920",
            "image_1024",
            "image_512",
            "image_256",
            "image_128",
            "lang",
            "tz",
            "tz_offset",
            "group_ids",
            "partner_id",
            "write_date",
            "action_id",
            "avatar_1920",
            "avatar_1024",
            "avatar_512",
            "avatar_256",
            "avatar_128",
            "share",
            "device_ids",
            "api_key_ids",
            "phone_ids",
            "display_name",
        ]

    @property
    def SELF_WRITEABLE_FIELDS(self) -> list[str]:
        return [
            "signature",
            "action_id",
            "company_id",
            "email",
            "name",
            "image_1920",
            "lang",
            "tz",
            "phone_ids",
        ]

    @api.model
    @tools.ormcache(cache="stable")
    def _get_self_accessible_fields(self) -> tuple[frozenset[str], frozenset[str]]:
        readable = frozenset(self.SELF_READABLE_FIELDS)
        writeable = frozenset(self.SELF_WRITEABLE_FIELDS)
        return readable, writeable

    @api.model
    def context_get(self) -> frozendict:
        context, user_lang_valid = self._get_context_cached()
        if context and not user_lang_valid and request:
            best_lang = request.best_lang
            if best_lang and best_lang != context["lang"]:
                if best_lang in self._get_installed_lang_codes():
                    return frozendict({**context, "lang": best_lang})
        return context

    @api.model
    @tools.ormcache()
    def _get_installed_lang_codes(self) -> tuple[str, ...]:
        return tuple(code for code, _name in self.env["res.lang"].get_installed())

    @api.model
    @tools.ormcache("self.env.uid")
    def _get_context_cached(self) -> tuple[frozendict, bool]:
        user = self.env.user.with_context(prefetch_fields=False)
        try:
            context = user.read(["lang", "tz"], load=False)[0]
        except IndexError:
            _debug.logic("context_user_missing", uid=self.env.uid)
            return frozendict(), False
        context.pop("id")

        langs = self._get_installed_lang_codes()
        langset = set(langs)
        user_lang_valid = context.get("lang") in langset

        def _lang_candidates():
            yield context.get("lang")
            yield user.company_id.partner_id.lang
            yield DEFAULT_LANG
            if langs:
                yield langs[0]

        context["lang"] = next(
            (lang for lang in _lang_candidates() if lang in langset), DEFAULT_LANG
        )

        context["uid"] = self.env.uid

        _debug.perf.count(
            "context_computed",
            uid=self.env.uid,
            lang=context["lang"],
            user_lang_valid=user_lang_valid,
        )
        return frozendict(context), user_lang_valid

    @tools.ormcache("self.id")
    def _get_company_ids(self) -> tuple[int, ...]:
        domain = [("active", "=", True), ("user_ids", "in", [self.id])]
        company_ids = self.env["res.company"].search(domain)._ids
        _debug.perf.count(
            "company_ids_computed", uid=self.id, companies=len(company_ids)
        )
        return company_ids

    @api.model
    @tools.ormcache("uid", "passwd_hash")
    def _check_uid_passwd_cached(
        self, uid: int, passwd: str, passwd_hash: str
    ) -> datetime.datetime | None:
        user = self.with_user(uid).env.user
        if not user.active:
            _debug.logic("uid_passwd_refused", uid=uid, reason="inactive")
            raise AccessDenied
        credential = {
            "login": user.login,
            "password": passwd,
            "type": "password",
        }
        result = user._check_credentials(credential, {"interactive": False})
        _debug.perf.count(
            "uid_passwd_cached", uid=uid, method=result.get("auth_method")
        )
        if result.get("auth_method") == "apikey":
            return self.env["res.users.apikeys"]._get_key_expiration(
                scope="rpc", key=passwd
            )
        return None

    @tools.ormcache("self.id", "sid")
    def _get_session_token(self, sid: str) -> str | bool:
        field_values = self._get_session_token_values()
        _debug.perf.count(
            "session_token_computed", uid=self.id, has_values=bool(field_values)
        )
        return self._hash_session_token(sid, field_values)

    @tools.ormcache("self.id")
    def _get_group_ids(self) -> tuple[int, ...]:
        self.check_singleton()
        group_ids = self.with_context({}).all_group_ids._ids
        _debug.perf.count("group_ids_computed", uid=self.id, groups=len(group_ids))
        return group_ids

    def _get_effective_group_ids(self) -> tuple[int, ...]:
        self.check_singleton()
        return self._get_group_ids() if self.id else self.all_group_ids._origin._ids

    def _password_store(self) -> PasswordStore:
        return PasswordStore(self.env)

    @tools.ormcache(cache="stable")
    def _get_crypt_context(self) -> CryptContext:
        return self._password_store().crypt_context()

    def _check_company_domain(self, companies: Self | str | None) -> Domain:
        if not companies:
            return Domain.TRUE
        company_ids = (
            companies if isinstance(companies, str) else models.to_record_ids(companies)
        )
        return Domain("company_ids", "in", company_ids)

    def _default_group_ids(self) -> Self:
        groups = self.env.ref("base.group_user")
        default_group = self.env.ref(
            "base.default_user_group", raise_if_not_found=False
        )
        if default_group:
            groups += default_group.implied_ids
        _debug.logic(
            "default_groups", default_group=bool(default_group), groups=len(groups)
        )
        return groups

    def _default_view_group_hierarchy(self) -> dict[str, Any]:
        return self.env["res.groups"]._get_view_group_hierarchy()

    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Related Partner",
        index=True,
        required=True,
        ondelete="restrict",
        bypass_search_access=True,
        help="Partner-related data of the user",
    )
    active_partner = fields.Boolean(
        related="partner_id.active",
        string="Partner is Active",
        readonly=True,
    )
    name = fields.Char(
        related="partner_id.name",
        inherited=True,
        readonly=False,
    )
    phone_ids = fields.Many2many(
        related="partner_id.phone_ids",
        inherited=True,
        readonly=False,
    )
    email = fields.Char(
        related="partner_id.email",
        inherited=True,
        readonly=False,
    )
    email_domain_placeholder = fields.Char(compute="_compute_email_domain_placeholder")

    active = fields.Boolean(default=True)

    login = fields.Char(
        required=True,
        help="Used to log into the system",
    )
    password = fields.Char(
        compute="_compute_passwords",
        inverse="_inverse_password",
        copy=False,
        help="Keep empty if you don't want the user to be able to connect on the system.",
    )
    new_password = fields.Char(
        string="Set Password",
        compute="_compute_passwords",
        inverse="_inverse_new_password",
        help="Specify a value only when creating a user or if you're "
        "changing the user's password, otherwise leave empty. After "
        "a change of password, the user has to login again.",
    )
    api_key_ids = fields.One2many(
        comodel_name="res.users.apikeys",
        inverse_name="user_id",
        string="API Keys",
    )
    signature = fields.Html(
        string="Email Signature",
        compute="_compute_signature",
        store=True,
        readonly=False,
    )

    action_id = fields.Many2one(
        comodel_name="ir.actions.actions",
        string="Home Action",
        help="If specified, this action will be opened at log on for this user, in addition to the standard menu.",
    )

    log_ids = fields.One2many(
        comodel_name="res.users.log",
        inverse_name="create_uid",
        string="User log entries",
    )
    login_date = fields.Datetime(
        related="log_ids.create_date",
        string="Latest Login",
    )

    device_ids = fields.One2many(
        comodel_name="res.device",
        inverse_name="user_id",
        string="User devices",
    )

    res_users_settings_ids = fields.One2many(
        comodel_name="res.users.settings",
        inverse_name="user_id",
    )
    res_users_settings_id = fields.Many2one(
        comodel_name="res.users.settings",
        string="Settings",
        compute="_compute_res_users_settings_id",
        search="_search_res_users_settings_id",
    )

    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company.id,
        required=True,
        context={"user_preference": True},
        help="The default company for this user.",
    )
    company_ids = fields.Many2many(
        comodel_name="res.company",
        relation="res_company_users_rel",
        column1="user_id",
        column2="cid",
        string="Companies",
        default=lambda self: self.env.company.ids,
    )
    companies_count = fields.Integer(
        string="Number of Companies",
        compute="_compute_companies_count",
    )

    group_ids = fields.Many2many(
        comodel_name="res.groups",
        relation="res_groups_users_rel",
        column1="uid",
        column2="gid",
        string="Groups",
        default=lambda s: s._default_group_ids(),
        help="Groups explicitly assigned to the user",
    )
    all_group_ids = fields.Many2many(
        comodel_name="res.groups",
        string="Groups and implied groups",
        compute="_compute_all_group_ids",
        search="_search_all_group_ids",
        compute_sudo=True,
    )
    share = fields.Boolean(
        string="Share User",
        compute="_compute_share",
        precompute=True,
        compute_sudo=True,
        store=True,
        help="External user with limited access, created only for the purpose of sharing data.",
    )

    accesses_count = fields.Integer(
        string="# Access Rights",
        compute="_compute_access_counts",
        compute_sudo=True,
        help="Number of access rights that apply to the current user",
    )
    rules_count = fields.Integer(
        string="# Record Rules",
        compute="_compute_access_counts",
        compute_sudo=True,
        help="Number of record rules that apply to the current user",
    )
    groups_count = fields.Integer(
        string="# Groups",
        compute="_compute_access_counts",
        compute_sudo=True,
        help="Number of groups that apply to the current user",
    )

    view_group_hierarchy = fields.Json(
        string="Technical field for user group setting",
        default=_default_view_group_hierarchy,
        store=False,
        copy=False,
    )
    role = fields.Selection(
        selection=[("group_user", "User"), ("group_system", "Administrator")],
        compute="_compute_role",
        inverse="_inverse_role",
        readonly=False,
    )

    def init(self) -> None:
        cr = self.env.cr

        if not sql.column_exists(cr, self._table, "password"):
            cr.execute("ALTER TABLE res_users ADD COLUMN password varchar")

        cr.execute(
            r"""
            SELECT id, password FROM res_users
            WHERE password IS NOT NULL
            AND password !~ '^\$[^$]+\$[^$]+\$.'
            """
        )
        rows = cr.fetchall()
        _debug.lifecycle("init_plaintext_passwords_hashed", count=len(rows))
        if rows:
            ctx = self._get_crypt_context()
            hashed = [(ctx.hash(pw), uid) for uid, pw in rows]
            cr.executemany("UPDATE res_users SET password=%s WHERE id=%s", hashed)
            self.sudo().browse([uid for uid, _pw in rows]).invalidate_recordset(
                ["password"]
            )

    _login_key = models.Constraint(
        "UNIQUE (login)", "You can not have two users with the same login!"
    )

    @api.constrains("company_id", "company_ids", "active")
    def _check_user_company(self) -> None:
        for user in self.filtered(lambda u: u.active):
            if user.company_id not in user.company_ids:
                _debug.logic(
                    "company_not_allowed", user=user.id, company=user.company_id.id
                )
                raise ValidationError(
                    _(
                        "Company %(company_name)s is not in the allowed companies for user %(user_name)s (%(company_allowed)s).",
                        company_name=user.company_id.name,
                        user_name=user.name,
                        company_allowed=", ".join(user.mapped("company_ids.name")),
                    )
                )

    @api.constrains("action_id")
    def _check_action_id(self) -> None:
        action_view_website = self.env.ref(
            "base.action_open_website", raise_if_not_found=False
        )
        if action_view_website and any(
            user.action_id.id == action_view_website.id for user in self
        ):
            _debug.logic("home_action_refused", users=self.ids, reason="app_launcher")
            raise ValidationError(
                _('The "App Launcher" action cannot be selected as home action.')
            )
        users_sudo = self.sudo()
        client_ids = []
        window_ids = []
        for user in users_sudo:
            if user.action_id.type == "ir.actions.client":
                client_ids.append(user.action_id.id)
            elif user.action_id.type == "ir.actions.act_window":
                window_ids.append(user.action_id.id)

        if client_ids:
            for action in self.env["ir.actions.client"].sudo().browse(client_ids):
                if action.tag == "reload":
                    _debug.logic(
                        "home_action_refused", action=action.id, reason="reload_tag"
                    )
                    raise ValidationError(
                        _(
                            'The "%s" action cannot be selected as home action.',
                            action.name,
                        )
                    )
        if window_ids:
            for action in self.env["ir.actions.act_window"].sudo().browse(window_ids):
                if action.context and "active_id" in action.context:
                    _debug.logic(
                        "home_action_refused",
                        action=action.id,
                        reason="needs_active_id",
                    )
                    raise ValidationError(
                        _(
                            'The action "%s" cannot be set as the home action because it requires a record to be selected beforehand.',
                            action.name,
                        )
                    )

    @api.constrains("group_ids")
    def _check_disjoint_groups(self) -> None:
        user_type_groups = self.env["res.groups"]._get_user_type_groups()
        for user in self:
            disjoint_groups = user.all_group_ids & user_type_groups
            if len(disjoint_groups) > 1:
                _debug.logic(
                    "disjoint_groups_violated", user=user.id, groups=disjoint_groups.ids
                )
                raise ValidationError(
                    _(
                        "User %(user)s cannot be at the same time in exclusive groups %(groups)s.",
                        user=repr(user.name),
                        groups=", ".join(repr(g.display_name) for g in disjoint_groups),
                    )
                )

    @api.constrains("group_ids", "active")
    def _check_at_least_one_administrator(self) -> None:
        if not self.env.registry.loaded_modules:
            _debug.logic("administrator_check_skipped", reason="registry_loading")
            return
        has_admin = (
            self.env["res.users"]
            .sudo()
            .search_count(
                [
                    ("all_group_ids", "in", self.env.ref("base.group_system").ids),
                    ("active", "=", True),
                ],
                limit=1,
            )
        )
        if not has_admin:
            _debug.logic("last_administrator_refused", users=self.ids)
            raise ValidationError(_("You must have at least an administrator user."))

    def _inverse_password(self) -> None:
        ctx = self._get_crypt_context()
        with _debug.perf("passwords_hashed", users=len(self)) as span:
            hashed = [
                (user.id, ctx.hash(user.password)) for user in self if user.password
            ]
            span.set(hashed=len(hashed))
        self.filtered(lambda user: not user.password)._clear_password()
        self._update_encrypted_passwords(hashed)

    def _clear_password(self) -> None:
        if not self:
            return
        self.flush_recordset(["password"])
        _debug.lifecycle("passwords_cleared", users=self.ids)
        self._password_store().clear(self)
        self.invalidate_recordset(["password"])
        self._invalidate_session_tokens()

    def _update_encrypted_password(self, uid: int, pw: str) -> None:
        self._update_encrypted_passwords([(uid, pw)])

    def _update_encrypted_passwords(self, hashed: list[tuple[int, str]]) -> None:
        if not hashed:
            return
        _debug.lifecycle("passwords_stored", users=[uid for uid, _pw in hashed])
        self._password_store().store(self, hashed)
        self.browse([uid for uid, _pw in hashed]).invalidate_recordset(["password"])
        self._invalidate_session_tokens()

    def _invalidate_session_tokens(self) -> None:
        _debug.lifecycle("session_tokens_invalidated", users=self.ids)
        self.env.registry.clear_cache()

    def _is_rpc_api_key_only(self) -> bool:
        return False

    def _check_credentials(
        self, credential: dict[str, Any], env: dict[str, Any]
    ) -> dict[str, Any]:
        self.check_singleton()
        if not (credential["type"] == "password" and credential.get("password")):
            _debug.logic(
                "credentials_refused",
                uid=self.id,
                reason="no_password",
                type=credential.get("type"),
            )
            raise AccessDenied

        interactive = env.get("interactive", True)

        if interactive or not self._is_rpc_api_key_only():
            if "interactive" not in env:
                _logger.warning(
                    "_check_credentials without 'interactive' env key, assuming interactive login. \
                    Check calls and overrides to ensure the 'interactive' key is properly set in \
                    all _check_credentials environments"
                )

            if self._password_store().stored_hash(self, self.id) is None:
                _debug.logic("credentials_refused", uid=self.id, reason="no_hash")
                raise AccessDenied
            valid, replacement = self._password_store().match_and_update(
                self, self.id, credential["password"]
            )
            _debug.logic(
                "password_checked",
                uid=self.id,
                valid=valid,
                rehashed=replacement is not None,
                interactive=interactive,
            )
            if replacement is not None:
                self._update_encrypted_password(self.id, replacement)
                if request and self == self.env.user:
                    _debug.pipeline("session_token_rotated", uid=self.id)
                    self.env.flush_all()
                    self.env.registry.clear_cache()
                    new_token = self._get_session_token(request.session.sid)
                    request.session.session_token = new_token

            if valid:
                return {
                    "uid": self.id,
                    "auth_method": "password",
                    "mfa": "default",
                }

        if not interactive:
            if (
                self.env["res.users.apikeys"]._check_credentials(
                    scope="rpc", key=credential["password"]
                )
                == self.id
            ):
                _debug.logic("apikey_checked", uid=self.id, valid=True)
                return {
                    "uid": self.id,
                    "auth_method": "apikey",
                    "mfa": "default",
                }

            if self._is_rpc_api_key_only():
                _logger.info(
                    "Invalid API key or password-based authentication attempted for a non-interactive (API) "
                    "context that requires API key authentication only."
                )

        _debug.logic(
            "credentials_refused",
            uid=self.id,
            reason="no_method_matched",
            interactive=interactive,
        )
        raise AccessDenied

    @api.depends_context("uid")
    def _compute_email_domain_placeholder(self) -> None:
        domain = email_domain_extract(self.env.user.email)
        self.email_domain_placeholder = (
            _("e.g. %(placeholder)s", placeholder=f"email@{domain}")
            if domain
            else _("Email")
        )

    def _compute_passwords(self) -> None:
        for user in self:
            user.password = ""
            user.new_password = ""

    def _inverse_new_password(self) -> None:
        for user in self:
            if not user.new_password:
                continue
            if user == self.env.user:
                _debug.logic("new_password_refused", uid=user.id, reason="own_user")
                raise UserError(
                    _(
                        "Please use the change password wizard (in User Preferences or User menu) to change your own password."
                    )
                )
            _debug.lifecycle("new_password_applied", uid=user.id, by=self.env.uid)
            user.password = user.new_password

    @api.depends("group_ids")
    def _compute_role(self) -> None:
        system_id = self._group_id("base.group_system")
        user_id = self._group_id("base.group_user")
        for user in self:
            gids = user._get_effective_group_ids()
            if system_id in gids:
                user.role = "group_system"
            elif user_id in gids:
                user.role = "group_user"
            else:
                user.role = False
        _debug.perf.count("role_computed", users=len(self))

    def _inverse_role(self) -> None:
        admin_id = self._group_id("base.group_system")
        user_id = self._group_id("base.group_user")
        for user in self:
            if not user.role:
                continue
            keep = user.group_ids.ids
            wanted = admin_id if user.role == "group_system" else user_id
            _debug.lifecycle("role_applied", user=user.id, role=user.role, group=wanted)
            user.group_ids = [
                Command.set(
                    [gid for gid in keep if gid not in (admin_id, user_id)] + [wanted]
                )
            ]

    @api.onchange("role")
    def _onchange_role(self) -> None:
        group_admin = self.env["res.groups"].new(
            origin=self.env.ref("base.group_system")
        )
        group_user = self.env["res.groups"].new(origin=self.env.ref("base.group_user"))
        for user in self:
            if user.role and user.has_group("base.group_user"):
                groups = user.group_ids - (group_admin + group_user)
                _debug.logic("onchange_role", user=user.id, role=user.role)
                user.group_ids = groups + (
                    group_admin if user.role == "group_system" else group_user
                )

    @api.depends("group_ids.all_implied_ids")
    def _compute_all_group_ids(self) -> None:
        for user in self:
            user.all_group_ids = user.group_ids.all_implied_ids

    def _search_all_group_ids(self, operator: str, value: Any) -> list:
        return [("group_ids.all_implied_ids", operator, value)]

    @api.depends("name")
    def _compute_signature(self) -> None:
        for user in self.filtered(
            lambda user: user.name and is_html_empty(user.signature)
        ):
            user.signature = Markup("<div>%s</div>") % user.name

    @api.depends("all_group_ids")
    def _compute_share(self) -> None:
        user_group_id = self._group_id("base.group_user")
        for user in self:
            user.share = user_group_id not in user.all_group_ids.ids
        _debug.perf.count(
            "share_computed",
            users=len(self),
            shared=sum(1 for user in self if user.share),
        )

    def _compute_companies_count(self) -> None:
        self.companies_count = self.env["res.company"].sudo().search_count([])

    @api.depends("all_group_ids")
    def _compute_access_counts(self) -> None:
        all_groups = self.all_group_ids
        accesses_per_group = dict.fromkeys(all_groups.ids, 0)
        rules_per_group: dict[int, set[int]] = {gid: set() for gid in all_groups.ids}
        if all_groups:
            for group, count in self.env["ir.model.access"]._read_group(
                [("group_id", "in", all_groups.ids)], ["group_id"], ["__count"]
            ):
                accesses_per_group[group.id] = count
            for rule in self.env["ir.rule"].search_fetch(
                [("groups", "in", all_groups.ids)], ["groups"]
            ):
                for group_id in rule.groups.ids:
                    if group_id in rules_per_group:
                        rules_per_group[group_id].add(rule.id)

        _debug.perf.count(
            "access_counts_computed",
            users=len(self),
            groups=len(all_groups),
            accesses=sum(accesses_per_group.values()),
            rules=len(set().union(*rules_per_group.values())),
        )
        for user in self:
            group_ids = user.all_group_ids.ids
            user.accesses_count = sum(accesses_per_group[gid] for gid in group_ids)
            user.rules_count = len(
                set().union(*(rules_per_group[g] for g in group_ids))
            )
            user.groups_count = len(group_ids)

    @api.depends("res_users_settings_ids")
    def _compute_res_users_settings_id(self) -> None:
        for user in self:
            user.res_users_settings_id = (
                user.res_users_settings_ids and user.res_users_settings_ids[0]
            )

    @api.model
    def _search_res_users_settings_id(self, operator: str, operand: Any) -> Domain:
        return Domain("res_users_settings_ids", operator, operand)

    @api.model
    @tools.ormcache()
    def _get_settings_backed_fields(self) -> frozenset[str]:
        return frozenset(
            name
            for name, field in self._fields.items()
            if field.related
            and field.related.startswith("res_users_settings_id.")
            and not field.readonly
        )

    def _is_settings_value_a_choice(self, name: str, value: Any) -> bool:
        if value:
            return True
        if self._fields[name].related.count(".") != 1:
            return True
        _, target_name = self._fields[name].related.split(".", 1)
        return not self.env["res.users.settings"]._fields[target_name].required

    @api.onchange("login")
    def _onchange_login(self) -> None:
        if self.login and tools.single_email_re.match(self.login):
            self.email = self.login

    @api.onchange("parent_id")
    def _onchange_parent_id(self) -> dict[str, Any] | None:
        return self.partner_id._onchange_parent_id()

    def onchange(
        self,
        values: dict[str, Any],
        field_names: list[str],
        fields_spec: dict[str, Any],
    ) -> dict[str, Any]:
        if self == self.env.user:
            user_sudo = self.sudo()
            fields_ = self._fields
            _debug.logic("onchange_self_prefetched", uid=self.env.uid)
            for field_name in self._get_self_accessible_fields()[0]:
                field = fields_[field_name]
                if field.type in ("binary", "one2many", "many2many"):
                    continue
                user_sudo[field_name]
        return super().onchange(values, field_names, fields_spec)

    def read(
        self,
        fields: collections.abc.Sequence[str] | None = None,
        load: str = "_classic_read",
    ) -> list[ValuesType]:
        readable, _ = self._get_self_accessible_fields()
        if (
            fields
            and self == self.env.user
            and all(key in readable or key.startswith("context_") for key in fields)
        ):
            _debug.logic("self_read_elevated", uid=self.env.uid, fields=list(fields))
            self = self.sudo()
        return super().read(fields=fields, load=load)

    def _has_field_access(self, field: Any, operation: str) -> bool:
        return super()._has_field_access(field, operation) or (
            operation == "read"
            and self._origin == self.env.user
            and field.name in self._get_self_accessible_fields()[0]
        )

    def _add_missing_settings_records(self) -> None:
        missing = self.sudo().filtered(lambda user: not user.res_users_settings_ids)
        if missing:
            _debug.lifecycle("settings_records_added", users=missing.ids)
            self.env["res.users.settings"].sudo().create(
                [{"user_id": user.id} for user in missing]
            )

    def _sync_partner_company(self) -> None:
        by_company = collections.defaultdict(lambda: self.env["res.partner"])
        for user in self:
            partner = user.partner_id
            if partner.company_id and partner.company_id != user.company_id:
                by_company[user.company_id.id] |= partner
        _debug.pipeline(
            "partner_company_synced", users=len(self), companies=len(by_company)
        )
        for company_id, partners in by_company.items():
            partners.write({"company_id": company_id})

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        backed = self._get_settings_backed_fields()
        deferred = [
            {
                k: v
                for k, v in vals.items()
                if k in backed and self._is_settings_value_a_choice(k, v)
            }
            for vals in vals_list
        ]
        if any(k in backed for vals in vals_list for k in vals):
            _debug.logic(
                "create_settings_fields_deferred",
                count=len(vals_list),
                fields=sorted({k for vals in vals_list for k in vals if k in backed}),
            )
            vals_list = [
                {k: v for k, v in vals.items() if k not in backed} for vals in vals_list
            ]
        users = super().create(vals_list)
        _debug.lifecycle(
            "create",
            count=len(users),
            logins=users.mapped("login"),
            deferred_settings=sum(1 for settings in deferred if settings),
        )
        users._sync_partner_company()
        inactive = users.filtered(lambda u: not u.active)
        _debug.pipeline(
            "create_partners_activated", users=len(users), inactive=len(inactive)
        )
        (users - inactive).partner_id.active = True
        inactive.partner_id.active = False
        users._update_missing_avatars()
        users.filtered(lambda user: user._is_internal())._add_missing_settings_records()
        for user, settings in zip(users, deferred, strict=True):
            if settings:
                user.write(settings)
        return users

    def _update_missing_avatars(self) -> None:
        generated = 0
        for user in self:
            if user.image_1920 or user.share or not (user.name or "").strip():
                continue
            generated += 1
            user.image_1920 = user.partner_id._prepare_avatar_svg()
        _debug.perf.count("avatars_generated", users=len(self), generated=generated)

    def _is_escaping_own_record(self, vals: dict[str, Any]) -> bool:
        for fname, value in vals.items():
            field = self._fields.get(fname)
            if field is None or field.type not in ("one2many", "many2many"):
                continue
            if field.type == "one2many":
                _debug.logic("own_record_escape", field=fname, reason="one2many")
                return True
            if isinstance(value, models.BaseModel) or not value:
                continue
            if not isinstance(value, (list, tuple)):
                _debug.logic("own_record_escape", field=fname, reason="not_commands")
                return True
            for command in value:
                if isinstance(command, (list, tuple)):
                    if not command or command[0] not in _RELATION_ONLY_COMMANDS:
                        _debug.logic(
                            "own_record_escape", field=fname, reason="write_command"
                        )
                        return True
                elif not isinstance(command, int):
                    _debug.logic("own_record_escape", field=fname, reason="not_an_id")
                    return True
        return False

    def write(self, vals: dict[str, Any]) -> bool:
        if vals.get("active") and SUPERUSER_ID in self._ids:
            _debug.logic("write_refused", users=self.ids, reason="activate_superuser")
            raise UserError(_("You cannot activate the superuser."))
        if vals.get("active") is False and self.env.uid in self._ids:
            _debug.logic("write_refused", users=self.ids, reason="deactivate_self")
            raise UserError(
                _("You cannot deactivate the user you're currently logged in as.")
            )

        if vals.get("active"):
            _debug.lifecycle("partners_unarchived", users=self.ids)
            self.partner_id.action_unarchive()

        if not self._get_settings_backed_fields().isdisjoint(vals):
            self._add_missing_settings_records()

        if self == self.env.user and vals:
            writeable = self._get_self_accessible_fields()[1]
            if all(
                key in writeable for key in vals
            ) and not self._is_escaping_own_record(vals):
                _debug.logic("self_write_elevated", uid=self.env.uid, fields=list(vals))
                self = self.sudo()

        _debug.lifecycle("write", count=len(self), fields=list(vals))
        res = super().write(vals)

        if "company_id" in vals:
            self._sync_partner_company()

        if "company_id" in vals or "company_ids" in vals:
            for env in list(self.env.transaction.envs):
                if env.user in self:
                    _debug.lifecycle("env_properties_reset", uid=env.uid)
                    reset_cached_properties(env)

        if "group_ids" in vals and self.ids:
            _debug.logic("write_cache_cleared", reason="group_ids")
            self.env["ir.model.access"].call_cache_clearing_methods()
        elif self._get_fields_invalidation() & vals.keys():
            _debug.logic("write_cache_cleared", reason="invalidating_fields")
            self.env.registry.clear_cache()

        return res

    @api.ondelete(at_uninstall=True)
    def _unlink_except_master_data(self) -> None:
        portal_user_template = self.env.ref("base.template_portal_user_id", False)
        public_user = self.env.ref("base.public_user", False)
        if SUPERUSER_ID in self.ids:
            _debug.logic("unlink_refused", users=self.ids, reason="superuser")
            raise UserError(
                _(
                    "You can not remove the admin user as it is used internally for resources created by Odoo (updates, module installation, ...)"
                )
            )
        user_admin = self.env.ref("base.user_admin", raise_if_not_found=False)
        if user_admin and user_admin in self:
            _debug.logic("unlink_refused", users=self.ids, reason="admin")
            raise UserError(
                _(
                    "You cannot delete the admin user because it is utilized in various places (such as security configurations,...). Instead, archive it."
                )
            )
        _debug.lifecycle("cache_cleared_before_unlink", users=self.ids)
        self.env.registry.clear_cache()
        if portal_user_template and portal_user_template in self:
            _debug.logic("unlink_refused", users=self.ids, reason="portal_template")
            raise UserError(
                _(
                    "Deleting the template users is not allowed. Deleting this profile will compromise critical functionalities."
                )
            )
        if public_user and public_user in self:
            _debug.logic("unlink_refused", users=self.ids, reason="public_user")
            raise UserError(
                _(
                    "Deleting the public user is not allowed. Deleting this profile will compromise critical functionalities."
                )
            )

    @api.model
    def name_search(
        self,
        name: str = "",
        domain: DomainType | None = None,
        operator: str = "ilike",
        limit: int = 100,
    ) -> list[tuple[int, str]]:
        domain = Domain(domain or Domain.TRUE)
        if (
            name
            and operator not in Domain.NEGATIVE_OPERATORS
            and (
                user := self.search_fetch(
                    Domain("login", "=", name) & domain, ["display_name"]
                )
            )
        ):
            _debug.logic("name_search_by_login", found=len(user))
            return [(u.id, u.display_name) for u in user]
        return super().name_search(name, domain, operator, limit)

    @api.model
    def _search_display_name(self, operator: str, value: Any) -> list:
        domain = super()._search_display_name(operator, value)
        if operator in ("in", "ilike") and value:
            name_domain = [
                ("login", "in", [value] if isinstance(value, str) else value)
            ]
            if users := self.search(name_domain):
                _debug.logic("display_name_search_by_login", found=len(users))
                domain = [("id", "in", users.ids)]
        return domain

    def copy_data(self, default: ValuesType | None = None) -> list[ValuesType]:
        default = dict(default or {})
        vals_list = super().copy_data(default=default)
        for user, vals in zip(self, vals_list, strict=True):
            if ("name" not in default) and ("partner_id" not in default):
                vals["name"] = _("%s (copy)", user.name)
            if "login" not in default:
                vals["login"] = _("%s (copy)", user.login)
        return vals_list

    @api.model
    def action_get(self) -> dict[str, Any]:
        return self.env.ref("base.action_res_users_my").sudo().read()[0]

    @api.model
    def _get_fields_invalidation(self) -> set[str]:
        return {
            "group_ids",
            "active",
            "lang",
            "tz",
            "company_id",
            "company_ids",
            *self._get_fields_session_token(),
        }

    @api.model
    def _update_last_login(self) -> None:
        self.env["res.users.log"].sudo().create({})

    @api.model
    def _get_domain_login(self, login: str) -> Domain:
        return Domain("login", "=", login)

    @api.model
    def _get_domain_email(self, email: str) -> Domain:
        return Domain("email", "=ilike", tools.escape_psql(email or ""))

    @api.model
    def _get_login_order(self) -> str:
        return self._order

    def _login(
        self, credential: dict[str, Any], user_agent_env: dict[str, Any]
    ) -> dict[str, Any]:
        login = credential["login"]
        ip = request.httprequest.environ["REMOTE_ADDR"] if request else "n/a"
        try:
            with self._assert_can_auth(user=login):
                user = self.sudo().search(
                    self._get_domain_login(login),
                    order=self._get_login_order(),
                    limit=1,
                )
                if not user:
                    _debug.logic("login_unknown", ip=ip)
                    self._get_crypt_context().match_and_update(
                        credential.get("password") or "", _DUMMY_PASSWORD_HASH
                    )
                    raise AccessDenied
                user = user.with_user(user).sudo()
                _debug.pipeline("login_credentials_check", uid=user.id, ip=ip)
                auth_info = user._check_credentials(credential, user_agent_env)
                tz = request.cookies.get("tz") if request else None
                if tz in all_timezones() and (not user.tz or not user.login_date):
                    _debug.logic("login_tz_adopted", uid=user.id, tz=tz)
                    user.tz = tz
                user._update_last_login()
        except AccessDenied:
            _logger.info("Login failed for login:%s from %s", login, ip)
            _debug.lifecycle("login_failed", login=login, ip=ip)
            raise

        _logger.info("Login successful for login:%s from %s", login, ip)
        _debug.lifecycle(
            "login", uid=auth_info["uid"], method=auth_info.get("auth_method"), ip=ip
        )

        return auth_info

    def authenticate(
        self, credential: dict[str, Any], user_agent_env: dict[str, Any]
    ) -> dict[str, Any]:
        auth_info = self._login(credential, user_agent_env=user_agent_env)
        if user_agent_env and user_agent_env.get("base_location"):
            env = self.env(user=auth_info["uid"])
            if env.user.has_group("base.group_system"):
                try:
                    base = user_agent_env["base_location"]
                    ICP = env["ir.config_parameter"]
                    frozen = bool(ICP.get_param("web.base.url.freeze"))
                    _debug.logic(
                        "base_url_from_login", uid=auth_info["uid"], frozen=frozen
                    )
                    if not frozen:
                        ICP.set_param("web.base.url", base)
                except Exception:
                    _logger.exception(
                        "Failed to update web.base.url configuration parameter"
                    )
        return auth_info

    @api.model
    def _check_uid_passwd(self, uid: int, passwd: str) -> None:
        if not passwd:
            _debug.logic("uid_passwd_refused", uid=uid, reason="empty")
            raise AccessDenied
        with self._assert_can_auth(user=uid):
            passwd_hash = sha256(passwd.encode()).hexdigest()
            key_expiration = self._check_uid_passwd_cached(uid, passwd, passwd_hash)
            if key_expiration is not None and key_expiration <= fields.Datetime.now():
                _debug.logic("uid_passwd_refused", uid=uid, reason="apikey_expired")
                raise AccessDenied

    def _get_fields_session_token(self) -> set[str]:
        return {"id", "login", "password", "active"}

    def _prepare_session_token_query_params(self) -> dict[str, SQL]:
        database_secret = SQL(
            "%s::text",
            self.env["ir.config_parameter"].sudo().get_param("database.secret"),
        )
        fields = SQL(", ").join(
            SQL.identifier(self._table, fname)
            for fname in sorted(self._get_fields_session_token())
            if not self._fields[fname].relational
        )
        return {
            "select": SQL("(%s) as database_secret, %s", database_secret, fields),
            "from": SQL("res_users"),
            "joins": SQL(""),
            "where": SQL("res_users.id = %s", self.id),
            "group_by": SQL("res_users.id"),
        }

    def _get_session_token_values(self) -> tuple[tuple[str, Any], ...] | bool:
        self.env.cr.execute(
            SQL(
                "SELECT %(select)s FROM %(from)s %(joins)s WHERE %(where)s GROUP BY %(group_by)s",
                **self._prepare_session_token_query_params(),
            )
        )
        if self.env.cr.rowcount != 1:
            _debug.logic(
                "session_token_values_missing", uid=self.id, rows=self.env.cr.rowcount
            )
            return False
        data_fields = self.env.cr.fetchone()
        cr_description = self.env.cr.description
        return tuple(
            (column.name, data_fields[index])
            for index, column in enumerate(cr_description)
        )

    def _hash_session_token(
        self, sid: str, field_values: tuple[tuple[str, Any], ...] | bool
    ) -> str | bool:
        return session_token(sid, field_values)

    @api.model
    def change_password(self, old_passwd: str, new_passwd: str) -> bool:
        if not old_passwd:
            _debug.logic("change_password_refused", uid=self.env.uid, reason="no_old")
            raise AccessDenied

        user = self.env.user
        credential = {
            "login": user.login,
            "password": old_passwd,
            "type": "password",
        }
        with self._assert_can_auth(user=user.id):
            user._check_credentials(credential, {"interactive": True})

        user._change_password(new_passwd)
        return True

    def _change_password(self, new_passwd: str) -> None:
        if not new_passwd.strip():
            _debug.logic("change_password_refused", uid=self.id, reason="empty")
            raise UserError(
                _("Setting empty passwords is not allowed for security reasons!")
            )

        ip = request.httprequest.environ["REMOTE_ADDR"] if request else "n/a"
        _logger.info(
            "Password change for %r (#%d) by %r (#%d) from %s",
            self.login,
            self.id,
            self.env.user.login,
            self.env.user.id,
            ip,
        )
        _debug.lifecycle("password_changed", uid=self.id, by=self.env.uid)

        self.password = new_passwd

    def _deactivate_portal_user(self, **post: Any) -> None:
        non_portal_users = self.filtered(lambda user: not user.share)
        if non_portal_users:
            _debug.logic("portal_deactivation_refused", users=non_portal_users.ids)
            raise AccessDenied(
                _(
                    "Only the portal users can delete their accounts. The user(s) %s can not be deleted.",
                    ", ".join(non_portal_users.mapped("name")),
                )
            )

        ip = request.httprequest.environ["REMOTE_ADDR"] if request else "n/a"

        res_users_deletion_values = []

        for user in self:
            _logger.info(
                'Account deletion asked for "%s" (#%i) from %s. Archive the user and remove login information.',
                user.login,
                user.id,
                ip,
            )

            user.write(
                {
                    "login": f"__deleted_user_{user.id}_{uuid.uuid4().hex}",
                    "password": "",
                }
            )
            _debug.lifecycle(
                "portal_user_scrubbed", uid=user.id, apikeys=len(user.api_key_ids)
            )
            user.api_key_ids._remove()

            res_users_deletion_values.append(
                {
                    "user_id": user.id,
                    "state": "todo",
                }
            )

        with contextlib.suppress(UserError, AccessError, ValidationError):
            self.with_user(SUPERUSER_ID).action_archive()
        with contextlib.suppress(UserError, AccessError, ValidationError):
            self.partner_id.action_archive()
        _debug.lifecycle(
            "portal_users_deactivated",
            users=self.ids,
            archived=not any(self.mapped("active")),
        )
        self.env["res.users.deletion"].create(res_users_deletion_values)

    def action_save_preferences(self) -> dict[str, Any]:
        return {
            "type": "ir.actions.client",
            "tag": "reload_context",
        }

    def action_change_password_wizard(self) -> dict[str, Any]:
        return {
            "type": "ir.actions.act_window",
            "target": "new",
            "res_model": "change.password.wizard",
            "view_mode": "form",
        }

    @check_identity
    def action_change_password(self) -> dict[str, Any]:
        return {
            "type": "ir.actions.act_window",
            "target": "new",
            "res_model": "change.password.own",
            "view_mode": "form",
        }

    @check_identity
    def action_open_api_key_wizard(self) -> dict[str, Any]:
        return {
            "type": "ir.actions.act_window",
            "res_model": "res.users.apikeys.description",
            "name": "New API Key",
            "target": "new",
            "views": [(False, "form")],
        }

    @check_identity
    def action_revoke_all_devices(self) -> dict[str, Any]:
        self.check_singleton()
        target = self.env.user if self.id == self.env.uid else self
        return target._action_revoke_all_devices()

    def _action_revoke_all_devices(self) -> dict[str, Any]:
        self.check_singleton()
        others = self.device_ids.filtered(lambda d: not d.is_current)
        _debug.lifecycle("all_devices_revoked", user=self.id, devices=len(others))
        others._revoke()
        return {"type": "ir.actions.client", "tag": "reload"}

    def _assert_group_query_allowed(self) -> None:
        if not (
            self.env.su
            or self == self.env.user
            or self.env.user._has_group("base.group_user")
        ):
            _debug.logic("group_query_refused", uid=self.env.uid, target=self.id)
            raise AccessError(
                _(
                    "Reading another user's groups requires an internal user; %(login)s is not one.",
                    login=self.env.user.login,
                )
            )

    @api.model
    def _group_id(self, group_ext_id: str) -> int | None:
        group_id = self.env["res.groups"]._get_group_definitions().get_id(group_ext_id)
        if group_id is None:
            _debug.logic("group_id_missing", group=group_ext_id)
            self._warn_unresolved_group(group_ext_id)
        return group_id

    @api.model
    def _warn_unresolved_group(self, group_ext_id: str) -> None:
        module = group_ext_id.split(".", 1)[0]
        if module not in self.env.registry.loaded_modules:
            return
        if group_ext_id in _UNRESOLVED_GROUPS_WARNED:
            return
        _UNRESOLVED_GROUPS_WARNED.add(group_ext_id)
        _debug.logic("group_unresolved", group=group_ext_id, module=module)
        _logger.warning(
            "Group %r does not exist though %r is loaded; the check answers "
            "'not a member', and a negated check answers 'everyone'.",
            group_ext_id,
            module,
        )

    def _has_group_effective(self, group_ext_id: str) -> bool:
        result = self._has_group(group_ext_id)
        if group_ext_id == DEBUG_GROUP:
            result = result and bool(request and request.session.debug)
            _debug.logic("debug_group_effective", uid=self.id, result=result)
        return result

    @api.readonly
    def has_groups(self, group_spec: str) -> bool:
        if group_spec == ".":
            return False

        self.check_singleton()
        self._assert_group_query_allowed()

        positives = []
        negatives = []
        for token in group_spec.split(","):
            token = token.strip()
            if not token:
                continue
            target = negatives if token.startswith("!") else positives
            target.append(token.removeprefix("!"))

        if not (positives or negatives):
            _debug.logic("has_groups_empty_spec", uid=self.id)
            return False

        if any(self._has_group_effective(ext_id) for ext_id in negatives):
            _debug.logic("has_groups_denied", uid=self.id, negatives=negatives)
            return False
        if any(self._has_group_effective(ext_id) for ext_id in positives):
            return True
        return not positives

    @api.readonly
    def has_group(self, group_ext_id: str) -> bool:
        self.check_singleton()
        self._assert_group_query_allowed()
        return self._has_group_effective(group_ext_id)

    def _has_group(self, group_ext_id: str) -> bool:
        group_id = self._group_id(group_ext_id)
        return group_id is not None and group_id in self._get_effective_group_ids()

    def has_any_group_id(self, group_ids: collections.abc.Collection[int]) -> bool:
        self.check_singleton()
        self._assert_group_query_allowed()

        group_ids = set(group_ids)
        if not (request and request.session.debug):
            group_ids.discard(self._group_id(DEBUG_GROUP))
        result = not group_ids.isdisjoint(self._get_effective_group_ids())
        _debug.logic("has_any_group", uid=self.id, groups=len(group_ids), result=result)
        return result

    def _action_show(self) -> dict[str, Any]:
        view_id = self.env.ref("base.view_users_form").id
        action = {
            "type": "ir.actions.act_window",
            "res_model": "res.users",
            "context": {"create": False},
        }
        if len(self) > 1:
            action.update(
                {
                    "name": _("Users"),
                    "view_mode": "list,form",
                    "views": [[None, "list"], [view_id, "form"]],
                    "domain": [("id", "in", self.ids)],
                }
            )
        else:
            action.update(
                {
                    "view_mode": "form",
                    "views": [[view_id, "form"]],
                    "res_id": self.id,
                }
            )
        return action

    def action_show_groups(self) -> dict[str, Any]:
        self.check_singleton()
        return {
            "name": _("Groups"),
            "view_mode": "list,form",
            "res_model": "res.groups",
            "type": "ir.actions.act_window",
            "context": {"create": False, "delete": False},
            "domain": [("id", "in", self.all_group_ids.ids)],
            "target": "current",
        }

    def action_show_accesses(self) -> dict[str, Any]:
        self.check_singleton()
        return {
            "name": _("Access Rights"),
            "view_mode": "list,form",
            "res_model": "ir.model.access",
            "type": "ir.actions.act_window",
            "context": {"create": False, "delete": False},
            "domain": [("id", "in", self.all_group_ids.model_access.ids)],
            "target": "current",
        }

    def action_show_rules(self) -> dict[str, Any]:
        self.check_singleton()
        return {
            "name": _("Record Rules"),
            "view_mode": "list,form",
            "res_model": "ir.rule",
            "type": "ir.actions.act_window",
            "context": {"create": False, "delete": False},
            "domain": [("id", "in", self.all_group_ids.rule_groups.ids)],
            "target": "current",
        }

    def _is_internal(self) -> bool:
        self.check_singleton()
        return self._has_group("base.group_user")

    def _is_portal(self) -> bool:
        self.check_singleton()
        return self._has_group("base.group_portal")

    def _is_public(self) -> bool:
        self.check_singleton()
        return self._has_group("base.group_public")

    def _is_system(self) -> bool:
        self.check_singleton()
        return self._has_group("base.group_system")

    def _is_admin(self) -> bool:
        self.check_singleton()
        return self._is_superuser() or self._has_group("base.group_erp_manager")

    def _is_superuser(self) -> bool:
        self.check_singleton()
        return self.id == SUPERUSER_ID

    def _login_cooldown(self) -> LoginCooldown:
        return LoginCooldown(self.pool)

    def _get_login_failure_state(self, source: str) -> tuple[int, datetime.datetime]:
        failures, last_failure = self._login_cooldown().state(source)
        _debug.logic("login_failure_state", source=source, failures=failures)
        return failures, last_failure

    def _record_login_failure(self, source: str) -> None:
        delay = self._get_login_cooldown_duration()
        _debug.lifecycle("login_failure_recorded", source=source, delay_s=delay)
        self._login_cooldown().record_failure(source, datetime.timedelta(seconds=delay))

    def _clear_login_failures(self, source: str) -> None:
        _debug.lifecycle("login_failures_cleared", source=source)
        self._login_cooldown().clear(source)

    @contextlib.contextmanager
    def _assert_can_auth(self, user: int | str | None = None) -> Generator[None]:
        if not request:
            _debug.logic("auth_cooldown_skipped", reason="no_request")
            yield
            return

        source = request.httprequest.remote_addr or "n/a"
        failures, previous = self._get_login_failure_state(source)
        if self._is_login_on_cooldown(failures, previous):
            _debug.logic("login_cooldown", source=source, failures=failures)
            _logger.warning(
                "Login attempt ignored for %s (user %r) on %s: "
                "%d failures since last success, last failure at %s. "
                "You can configure the number of login failures before a "
                "user is put on cooldown as well as the duration in the "
                "System Parameters. Disable this feature by setting "
                '"base.login_cooldown_after" to 0.',
                source,
                user or "?",
                self.env.cr.dbname,
                failures,
                previous,
            )
            if _is_private_address(source):
                _logger.warning(
                    "The rate-limited IP address %s is classified as private "
                    "and *might* be a proxy. If your Odoo is behind a proxy, "
                    "it may be mis-configured. Check that you are running "
                    "Odoo in Proxy Mode and that the proxy is properly configured, see "
                    "https://www.odoo.com/documentation/latest/administration/install/deploy.html#https for details.",
                    source,
                )
            raise AccessDenied(
                _("Too many login failures, please wait a bit before trying again.")
            )

        try:
            yield
        except AccessDenied:
            self._record_login_failure(source)
            raise
        else:
            self._clear_login_failures(source)

    def _get_login_cooldown_duration(self) -> int:
        return (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param_int("base.login_cooldown_duration", 60)
        )

    def _is_login_on_cooldown(self, failures: int, previous: datetime.datetime) -> bool:
        min_failures = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param_int("base.login_cooldown_after", 10)
        )
        if min_failures <= 0:
            _debug.logic("login_cooldown_disabled")
            return False

        delay = self._get_login_cooldown_duration()
        on_cooldown = failures >= min_failures and (
            datetime.datetime.now(datetime.UTC) - previous
        ) < datetime.timedelta(seconds=delay)
        _debug.logic(
            "login_cooldown_evaluated",
            failures=failures,
            min_failures=min_failures,
            delay_s=delay,
            on_cooldown=on_cooldown,
        )
        return on_cooldown

    def _get_mfa_type(self) -> str | None:
        return

    def _get_mfa_url(self) -> str | None:
        return

    @api.model
    def fields_get(
        self,
        allfields: collections.abc.Collection[str] | None = None,
        attributes: collections.abc.Collection[str] | None = None,
    ) -> dict[str, ValuesType]:
        res = super().fields_get(allfields, attributes=attributes)

        readable_fields, writeable_fields = self._get_self_accessible_fields()
        missing = (writeable_fields | readable_fields).difference(res.keys())
        if allfields:
            missing = missing.intersection(allfields)
        if missing:
            _debug.logic("fields_get_self_fields_added", fields=sorted(missing))
            self = self.sudo()
            res.update(
                {
                    key: dict(
                        values,
                        readonly=key not in writeable_fields,
                        searchable=False,
                    )
                    for key, values in super()
                    .fields_get(sorted(missing), attributes)
                    .items()
                }
            )
        return res

    def _get_view_postprocessed(
        self, view: Any, arch: bytes, **options: Any
    ) -> tuple[bytes, dict[str, Any]]:
        arch, models = super()._get_view_postprocessed(view, arch, **options)
        if view == self.env.ref("base.view_users_form_simple_modif"):
            tree = etree.fromstring(arch)
            readable = self._get_self_accessible_fields()[0]
            ungrouped = 0
            for node_field in tree.xpath("//field[@__groups_key__]"):
                if node_field.get("name") in readable:
                    ungrouped += 1
                    node_field.attrib.pop("__groups_key__")
            _debug.pipeline("preferences_view_postprocessed", ungrouped=ungrouped)
            arch = etree.tostring(tree)
        return arch, models


ResUsersPatchedInTest = ResUsers


class UsersMultiCompany(models.Model):
    _inherit = "res.users"

    def _resolve_multi_company_group_membership(self, group_id: int) -> bool | None:
        self.check_singleton()
        user = self.sudo()
        is_member = group_id in user.group_ids.ids
        wanted = len(user.company_ids) > 1
        return None if wanted == is_member else wanted

    def _sync_multi_company_group(self) -> None:
        group_id = self._group_id("base.group_multi_company")
        if not group_id:
            _debug.logic("multi_company_sync_skipped", reason="no_group")
            return
        to_add = to_remove = self.browse()
        for user in self:
            wanted = user._resolve_multi_company_group_membership(group_id)
            if wanted is True:
                to_add |= user
            elif wanted is False:
                to_remove |= user
        _debug.lifecycle(
            "multi_company_group_synced",
            users=len(self),
            added=to_add.ids,
            removed=to_remove.ids,
        )
        if to_remove:
            to_remove.write({"group_ids": [Command.unlink(group_id)]})
        if to_add:
            to_add.write({"group_ids": [Command.link(group_id)]})

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        users = super().create(vals_list)
        users._sync_multi_company_group()
        return users

    def write(self, vals: dict[str, Any]) -> bool:
        res = super().write(vals)
        if "company_ids" in vals:
            self._sync_multi_company_group()
        return res

    @api.model
    def new(
        self,
        values: ValuesType | None = None,
        origin: Self | None = None,
        ref: str | None = None,
    ) -> Self:
        if values is None:
            values = {}
        user = super().new(values=values, origin=origin, ref=ref)
        group_id = self._group_id("base.group_multi_company")
        if group_id:
            wanted = user._resolve_multi_company_group_membership(group_id)
            if wanted is not None:
                _debug.logic("multi_company_group_on_new", wanted=wanted)
                command = Command.link(group_id) if wanted else Command.unlink(group_id)
                user.update({"group_ids": [command]})
        return user
