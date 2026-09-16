import ast
import re
import typing
from collections import defaultdict
from collections.abc import Iterable
from typing import Literal, Self

from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.api import ValuesType
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools import is_html_empty, ormcache, remove_accents

if typing.TYPE_CHECKING:
    from .mail_alias_domain import MailAliasDomain
    from odoo.addons.base.models.ir_model import IrModel
    from odoo.addons.base.models.res_company import ResCompany

_debug = DebugLog(__name__)

atext = r"[a-zA-Z0-9!#$%&'*+\-/=?^_`{|}~]"
dot_atom_text = re.compile(r"^%s+(\.%s+)*$" % (atext, atext))
alias_invalid_chars = re.compile(r"[^\w!#$%&'*+\-/=?^_`{|}~.]+")
alias_dot_runs = re.compile(r"^\.+|\.+$|\.+(?=\.)")
dns_name = re.compile(r"^(?!-)[a-z0-9-]{1,63}(?<!-)(\.(?!-)[a-z0-9-]{1,63}(?<!-))*$")
DNS_NAME_MAX = 253
alias_document_fields = {
    "owner": ("alias_parent_model_id", "alias_parent_thread_id"),
    "target": ("alias_model_id", "alias_force_thread_id"),
}


class AliasAddresses(typing.NamedTuple):
    full_names: frozenset[str]
    local_names: frozenset[str]
    by_parent: dict[tuple[str, int], str]


class MailAlias(models.Model):
    _name = "mail.alias"
    _description = "Email Aliases"
    _order = "alias_model_id, alias_name"
    _rec_name = "alias_name"
    _rec_names_search = ["alias_full_name"]

    alias_name = fields.Char(
        copy=False,
        help="The name of the email alias, e.g. 'jobs' if you want to catch emails for <jobs@example.odoo.com>",
    )
    alias_full_name = fields.Char(
        string="Alias Email",
        compute="_compute_alias_full_name",
        store=True,
        index="btree_not_null",
    )
    alias_domain_id: MailAliasDomain = fields.Many2one(
        comodel_name="mail.alias.domain",
        default=lambda self: self.env.company.alias_domain_id,
        ondelete="restrict",
    )
    alias_domain = fields.Char(
        related="alias_domain_id.name",
        string="Alias domain name",
    )
    alias_model_id: IrModel = fields.Many2one(
        comodel_name="ir.model",
        string="Aliased Model",
        required=True,
        domain="[('field_id.name', '=', 'message_ids'), ('abstract', '=', False), ('transient', '=', False)]",
        ondelete="cascade",
        help="The model (Odoo Document Kind) to which this alias "
        "corresponds. Any incoming email that does not reply to an "
        "existing record will cause the creation of a new record "
        "of this model (e.g. a Project Task)",
    )
    alias_defaults = fields.Text(
        string="Default Values",
        default="{}",
        required=True,
        help="A Python dictionary that will be evaluated to provide "
        "default values when creating new records for this alias.",
    )
    alias_force_thread_id = fields.Integer(
        string="Record Thread ID",
        help="Optional ID of a thread (record) to which all incoming messages will be attached, even "
        "if they did not reply to it. If set, this will disable the creation of new records completely.",
    )
    alias_parent_model_id: IrModel = fields.Many2one(
        comodel_name="ir.model",
        string="Parent Model",
        help="Parent model holding the alias. The model holding the alias reference "
        "is not necessarily the model given by alias_model_id "
        "(example: project (parent_model) and task (model))",
    )
    alias_parent_thread_id = fields.Integer(
        string="Parent Record Thread ID",
        help="ID of the parent record holding the alias (example: project holding the task creation alias)",
    )
    alias_contact = fields.Selection(
        selection=[
            ("everyone", "Everyone"),
            ("partners", "Authenticated Partners"),
            ("followers", "Followers only"),
        ],
        string="Alias Contact Security",
        default="everyone",
        required=True,
        help="Policy to post a message on the document using the mailgateway.\n"
        "- everyone: everyone can post\n"
        "- partners: only authenticated partners\n"
        "- followers: only followers of the related document or members of following channels\n",
    )
    alias_incoming_local = fields.Boolean(
        string="Local-part based incoming detection",
        default=False,
    )
    alias_bounced_content = fields.Html(
        string="Custom Bounced Message",
        translate=True,
        help="If set, this content will automatically be sent out to unauthorized users instead of the default message.",
    )
    alias_status = fields.Selection(
        selection=[
            ("not_tested", "Not Tested"),
            ("valid", "Valid"),
            ("invalid", "Invalid"),
        ],
        default="not_tested",
        help="Alias status assessed on the last message received.",
    )

    ALIAS_STATUS_NEUTRAL = frozenset(
        {
            "alias_status",
            "alias_bounced_content",
            "alias_name",
            "alias_domain_id",
        }
    )
    ALIAS_ADDRESS_FIELDS = frozenset(
        {
            "alias_name",
            "alias_domain_id",
            "alias_incoming_local",
            "alias_parent_model_id",
            "alias_parent_thread_id",
        }
    )

    _name_domain_unique = models.UniqueIndex(
        "(alias_name, COALESCE(alias_domain_id, 0))",
        "This email alias is already used on another record.",
    )

    @api.constrains(
        "alias_domain_id",
        "alias_force_thread_id",
        "alias_parent_model_id",
        "alias_parent_thread_id",
        "alias_model_id",
    )
    def _check_alias_domain_id_mc(self) -> None:
        tocheck = self.filtered(
            lambda alias: (
                alias.alias_domain_id.company_ids
                and all(
                    not alias[model_fname].model or alias[model_fname].model in self.env
                    for model_fname, _thread_fname in alias_document_fields.values()
                )
            )
        )
        if not tocheck:
            return

        ids_by_model = defaultdict(set)
        for alias in tocheck:
            for model_fname, thread_fname in alias_document_fields.values():
                model = alias[model_fname].model
                thread_id = alias[thread_fname]
                if model and thread_id and self.env[model]._mail_get_company_field():
                    ids_by_model[model].add(thread_id)

        ids_by_model = {
            model: set(self.env[model].browse(thread_ids).exists().ids)
            for model, thread_ids in ids_by_model.items()
        }

        for alias in tocheck:
            for kind, (model_fname, thread_fname) in alias_document_fields.items():
                model = alias[model_fname].model
                if alias[thread_fname] not in ids_by_model.get(model, ()):
                    continue
                document = (
                    self.env[model]
                    .with_prefetch(tuple(ids_by_model[model]))
                    .browse(alias[thread_fname])
                )
                company = document[document._mail_get_company_field()]
                if not company or company.alias_domain_id == alias.alias_domain_id:
                    continue
                raise self._alias_prepare_domain_mc_error(alias, company, kind)

    @api.model
    def _alias_prepare_domain_mc_error(
        self, alias: MailAlias, company: models.Model, kind: Literal["owner", "target"]
    ) -> ValidationError:
        values = {
            "alias_company_names": ",".join(
                alias.alias_domain_id.company_ids.mapped("name")
            ),
            "alias_domain_name": alias.alias_domain_id.name,
            "alias_name": alias.display_name,
            "company_name": company.name,
        }
        if kind == "owner":
            return ValidationError(
                _(
                    "We could not create alias %(alias_name)s because domain "
                    "%(alias_domain_name)s belongs to company %(alias_company_names)s "
                    "while the owner document belongs to company %(company_name)s.",
                    **values,
                )
            )
        return ValidationError(
            _(
                "We could not create alias %(alias_name)s because domain "
                "%(alias_domain_name)s belongs to company %(alias_company_names)s "
                "while the target document belongs to company %(company_name)s.",
                **values,
            )
        )

    @api.model
    def _alias_name_is_valid(self, name: str) -> bool:
        return bool(name) and self._normalize_alias_name(name) == name

    @api.constrains("alias_name")
    def _check_alias_name_is_normalized(self) -> None:
        for alias in self.filtered("alias_name"):
            if not self._alias_name_is_valid(alias.alias_name):
                raise ValidationError(
                    _(
                        "You cannot use anything else than unaccented lowercase latin characters in the alias address %(alias_name)s.",
                        alias_name=alias.alias_name,
                    )
                )

    @api.model
    def _alias_model_accepts_mail(self, model: models.BaseModel) -> bool:
        return self.env["mixin.mail.gateway"]._mail_is_gateway_target(model)

    @api.constrains("alias_model_id")
    def _check_alias_model_accepts_mail(self) -> None:
        for alias in self:
            model = alias.alias_model_id.model
            if not model or model not in self.env:
                continue
            if not self._alias_model_accepts_mail(self.env[model]):
                raise ValidationError(
                    _(
                        "An alias can only target a model that accepts incoming "
                        "mail, and %(model_name)s does not.",
                        model_name=alias.alias_model_id.display_name or model,
                    )
                )

    @api.constrains("alias_defaults", "alias_model_id")
    def _check_alias_defaults(self) -> None:
        for alias in self:
            try:
                defaults = alias._prepare_alias_defaults()
            except Exception as e:
                raise ValidationError(
                    _(
                        "Invalid expression, it must be a literal python dictionary definition e.g. \"{'field': 'value'}\""
                    )
                ) from e
            model = alias.alias_model_id.model
            if not model or model not in self.env:
                continue
            fields_ = self.env[model]._fields
            unknown = sorted(set(defaults) - set(fields_))
            if unknown:
                raise ValidationError(
                    _(
                        "Default values %(field_names)s are not fields of %(model_name)s.",
                        field_names=", ".join(unknown),
                        model_name=alias.alias_model_id.display_name,
                    )
                )
            dropped = sorted(
                fname
                for fname in defaults
                if fields_[fname].compute
                and fields_[fname].readonly
                and not fields_[fname].inverse
                and not fields_[fname].inherited
            )
            if dropped:
                raise ValidationError(
                    _(
                        "Default values %(field_names)s cannot be set on "
                        "%(model_name)s: they are computed fields.",
                        field_names=", ".join(dropped),
                        model_name=alias.alias_model_id.display_name,
                    )
                )

    def _prepare_alias_defaults(self) -> dict:
        self.check_singleton()
        defaults = ast.literal_eval(self.alias_defaults or "{}")
        if not isinstance(defaults, dict):
            msg = f"alias_defaults must be a dict, got {type(defaults).__name__}"
            raise ValueError(msg)
        if unnamed := [key for key in defaults if not isinstance(key, str)]:
            msg = f"alias_defaults keys must be field names, got {unnamed!r}"
            raise ValueError(msg)
        return defaults

    @api.constrains("alias_name", "alias_domain_id", "alias_incoming_local")
    def _check_alias_domain_clash(self) -> None:
        named = self.filtered("alias_name")
        failing = named.filtered(
            lambda alias: (
                not alias.alias_incoming_local
                and alias.alias_name
                in [
                    alias.alias_domain_id.bounce_alias,
                    alias.alias_domain_id.catchall_alias,
                ]
            )
        )
        if local := named.filtered("alias_incoming_local"):
            reserved = self.env["mail.alias.domain"]._get_reserved_local_parts()
            failing |= local.filtered(lambda alias: alias.alias_name in reserved)
        if failing:
            raise ValidationError(
                _(
                    "Aliases %(alias_names)s are already used as bounce or catchall address. Please choose another alias.",
                    alias_names=", ".join(failing.mapped("display_name")),
                )
            )

    @api.depends("alias_domain_id.name", "alias_name")
    def _compute_alias_full_name(self) -> None:
        for record in self:
            if record.alias_domain_id and record.alias_name:
                record.alias_full_name = (
                    f"{record.alias_name}@{record.alias_domain_id.name}"
                )
            elif record.alias_name:
                record.alias_full_name = record.alias_name
            else:
                record.alias_full_name = False

    @api.depends("alias_full_name")
    def _compute_display_name(self) -> None:
        for record in self:
            record.display_name = record.alias_full_name or _("Inactive Alias")

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        defaults = None
        prepared = []
        for vals in vals_list:
            vals = dict(vals)
            if "alias_name" not in vals or "alias_domain_id" not in vals:
                if defaults is None:
                    defaults = self.default_get(["alias_name", "alias_domain_id"])
                vals.setdefault("alias_name", defaults.get("alias_name", False))
                vals.setdefault(
                    "alias_domain_id", defaults.get("alias_domain_id", False)
                )
            prepared.append(vals)

        self._update_alias_name_vals(prepared)
        AliasDomain = self.env["mail.alias.domain"]
        self._check_alias_address_available(
            [
                (vals["alias_name"], AliasDomain.browse(vals["alias_domain_id"]))
                for vals in prepared
            ]
        )
        _debug.lifecycle(
            "create",
            count=len(prepared),
            named=sum(1 for vals in prepared if vals["alias_name"]),
            defaulted=defaults is not None,
        )
        aliases = super().create(prepared)
        self.env.registry.clear_cache("mail")
        return aliases

    def write(self, vals: ValuesType) -> Literal[True]:
        if "alias_status" not in vals and not self.ALIAS_STATUS_NEUTRAL.issuperset(
            vals
        ):
            vals = {**vals, "alias_status": "not_tested"}
        _debug.lifecycle("write", aliases=self.ids, fields=list(vals))

        if "alias_name" in vals or "alias_domain_id" in vals:
            vals = dict(vals)
            self._update_alias_name_vals([vals])
            AliasDomain = self.env["mail.alias.domain"]
            addresses = [
                (
                    vals.get("alias_name", record.alias_name),
                    AliasDomain.browse(vals["alias_domain_id"])
                    if "alias_domain_id" in vals
                    else record.alias_domain_id,
                )
                for record in self
            ]
            if any(
                address != (record.alias_name, record.alias_domain_id)
                for address, record in zip(addresses, self, strict=True)
            ):
                self._check_alias_address_available(addresses)

        result = super().write(vals)
        if not self.ALIAS_ADDRESS_FIELDS.isdisjoint(vals):
            self.env.registry.clear_cache("mail")
        return result

    def unlink(self) -> Literal[True]:
        result = super().unlink()
        self.env.registry.clear_cache("mail")
        return result

    @api.model
    @ormcache(cache="mail")
    def _get_alias_addresses(self) -> AliasAddresses:
        aliases = self.sudo().search_fetch(
            [("alias_name", "!=", False)],
            [
                "alias_full_name",
                "alias_name",
                "alias_incoming_local",
                "alias_domain_id",
                "alias_parent_model_id",
                "alias_parent_thread_id",
            ],
        )
        _debug.perf.count("addresses_computed", aliases=len(aliases))
        by_parent: dict[tuple[str, int], str] = {}
        for alias in aliases:
            if alias.alias_domain_id and alias.alias_parent_thread_id:
                by_parent.setdefault(
                    (alias.alias_parent_model_id.model, alias.alias_parent_thread_id),
                    alias.alias_full_name,
                )
        return AliasAddresses(
            frozenset(
                alias.alias_full_name
                for alias in aliases
                if alias.alias_full_name and not alias.alias_incoming_local
            ),
            frozenset(
                alias.alias_name for alias in aliases if alias.alias_incoming_local
            ),
            by_parent,
        )

    @api.model
    def _update_alias_name_vals(self, vals_list: list[ValuesType]) -> None:
        pending = []
        for vals in vals_list:
            if "alias_name" not in vals:
                continue
            raw = vals["alias_name"]
            domain_part = raw.partition("@")[2].strip() if isinstance(raw, str) else ""
            vals["alias_name"] = self._normalize_alias_name(raw)
            if domain_part and vals["alias_name"]:
                pending.append((vals, domain_part))
        if not pending:
            return

        sanitized = {
            domain_part: self._normalize_alias_domain_name(domain_part)
            for _vals, domain_part in pending
        }
        wanted = {name for name in sanitized.values() if name}
        found = (
            {
                domain.name: domain.id
                for domain in self.env["mail.alias.domain"].search(
                    [("name", "in", list(wanted))]
                )
            }
            if wanted
            else {}
        )
        _debug.logic("alias_domain_from_name", pending=len(pending), found=len(found))
        for vals, domain_part in pending:
            domain_name = sanitized[domain_part]
            if not domain_name:
                continue
            if domain_name in found:
                vals["alias_domain_id"] = found[domain_name]
            elif "." in domain_name:
                raise ValidationError(
                    _(
                        "There is no alias domain %(domain_name)s. Create it first, or "
                        "enter %(alias_name)s alone and pick a domain.",
                        alias_name=vals["alias_name"],
                        domain_name=domain_part,
                    )
                )

    def _check_alias_address_available(
        self, addresses: Iterable[tuple[str, MailAliasDomain]]
    ) -> None:
        domain_to_names = defaultdict(list)
        for alias_name, alias_domain in addresses:
            if not alias_name:
                continue
            if alias_name in domain_to_names[alias_domain]:
                raise UserError(
                    _(
                        "Email aliases %(alias_name)s cannot be used on several records at the same time. Please update records one by one.",
                        alias_name=alias_name,
                    )
                )
            domain_to_names[alias_domain].append(alias_name)

        if not domain_to_names:
            return
        domain = Domain.OR(
            Domain("alias_name", "in", names)
            & Domain("alias_domain_id", "=", alias_domain.id)
            for alias_domain, names in domain_to_names.items()
        )
        if self:
            domain &= Domain("id", "not in", self.ids)
        if existing := self.sudo().search(domain, limit=1):
            _debug.logic(
                "alias_address_taken",
                aliases=self.ids,
                existing=existing.id,
                name=existing.alias_name,
            )
            self._alias_raise_address_taken(existing)

    def _alias_raise_address_taken(self, existing: Self) -> typing.NoReturn:
        values = {
            "address": existing.display_name,
            "alias_model_name": existing.alias_model_id.name,
            "matching_id": existing.id,
        }
        if parent := existing._alias_get_document("owner"):
            raise UserError(
                _(
                    "The address %(address)s is already taken by alias %(matching_id)s, "
                    "which targets %(alias_model_name)s and belongs to the "
                    "%(parent_model_name)s %(parent_name)s. Choose another address, or "
                    "change it on that document.",
                    parent_model_name=existing.alias_parent_model_id.name,
                    parent_name=parent.display_name,
                    **values,
                )
            )
        raise UserError(
            _(
                "The address %(address)s is already taken by alias %(matching_id)s, "
                "which targets %(alias_model_name)s. Choose another address, or change "
                "it on that document.",
                **values,
            )
        )

    @api.model
    def _normalize_alias_name(
        self, name: str, is_email: bool = False
    ) -> str | Literal[False]:
        if not name:
            return False
        local_part, _sep, domain_part = name.strip().partition("@")
        local_part = (
            remove_accents(local_part).encode("ascii", errors="ignore").decode().lower()
        )
        local_part = alias_invalid_chars.sub("-", local_part)
        local_part = alias_dot_runs.sub("", local_part)
        if not local_part:
            return False
        if not is_email or not domain_part:
            return local_part
        domain_part = self._normalize_alias_domain_name(domain_part)
        return f"{local_part}@{domain_part}" if domain_part else False

    @api.model
    def _normalize_alias_domain_name(self, domain_name: str) -> str | Literal[False]:
        domain_name = domain_name.strip().lower()
        if not domain_name:
            return False
        if not domain_name.isascii():
            try:
                domain_name = domain_name.encode("idna").decode("ascii")
            except UnicodeError:
                return False
        if len(domain_name) > DNS_NAME_MAX or not dns_name.match(domain_name):
            return False
        return domain_name

    def open_document(self) -> dict | Literal[False]:
        return self._alias_open_document("target")

    def open_parent_document(self) -> dict | Literal[False]:
        return self._alias_open_document("owner")

    def _alias_open_document(
        self, kind: Literal["owner", "target"]
    ) -> dict | Literal[False]:
        self.check_singleton()
        model_fname, thread_fname = alias_document_fields[kind]
        if not self[model_fname] or not self[thread_fname]:
            return False
        return {
            "view_mode": "form",
            "res_model": self[model_fname].model,
            "res_id": self[thread_fname],
            "type": "ir.actions.act_window",
        }

    def _alias_get_document(
        self, kind: Literal["owner", "target"]
    ) -> models.Model | None:
        self.check_singleton()
        model_fname, thread_fname = alias_document_fields[kind]
        model = self[model_fname].model
        thread_id = self[thread_fname]
        if not model or not thread_id or model not in self.env:
            return None
        return self.env[model].browse(thread_id).exists() or None

    def _alias_get_company(self) -> ResCompany:
        self.check_singleton()
        for kind in alias_document_fields:
            document = self._alias_get_document(kind)
            if document is None:
                continue
            company_fname = document._mail_get_company_field()
            if company_fname and document[company_fname]:
                return document[company_fname]
        return self.alias_domain_id.company_ids[:1] or self.env.company

    def _alias_mark_valid(self) -> None:
        for alias in self:
            if alias.alias_status != "valid":
                _debug.lifecycle("alias_status", alias=alias.id, status="valid")
                alias.sudo().alias_status = "valid"

    def _alias_mark_invalid(self) -> None:
        _debug.lifecycle("alias_status", aliases=self.ids, status="invalid")
        self.sudo().alias_status = "invalid"

    def _alias_with_author_lang(self, message_dict: dict) -> Self:
        self.check_singleton()
        partner = self.env["res.partner"].sudo().browse(message_dict.get("author_id"))
        lang = partner.exists().lang
        return self.with_context(lang=lang) if lang else self

    def _alias_bounce_wrap(self, content: Markup) -> Markup:
        return Markup(
            "<p>%(header)s,<br /><br />%(content)s<br /><br />%(regards)s</p>"
        ) % {
            "content": content,
            "header": _("Dear Sender"),
            "regards": _("Kind Regards"),
        }

    def _alias_bounce_render(self, body: Markup, message_dict: dict) -> Markup:
        return self.env["ir.qweb"]._render(
            "mail.mail_bounce_alias_security",
            {
                "body": body,
                "message": {**message_dict, "body": message_dict.get("body") or ""},
            },
            minimal_qcontext=True,
        )

    def _get_alias_bounced_body(self, message_dict: dict) -> Markup:
        self.check_singleton()
        self = self._alias_with_author_lang(message_dict)
        if is_html_empty(self.alias_bounced_content):
            body = self._alias_bounce_wrap(
                self._get_alias_bounced_body_fallback(message_dict)
            )
        else:
            body = self.alias_bounced_content
        return self._alias_bounce_render(body, message_dict)

    def _get_alias_bounced_body_fallback(self, message_dict: dict) -> Markup:
        company = self._alias_get_company()
        default_email = (
            company.partner_id.email_formatted
            if company.partner_id.email
            else company.name
        )
        return Markup(
            _(
                "The message below could not be accepted by the address "
                "%(alias_display_name)s. Only %(contact_description)s are allowed to "
                "contact it.<br /><br />Please make sure you are using the correct "
                "address or contact us at %(default_email)s instead."
            )
        ) % {
            "alias_display_name": self.display_name,
            "contact_description": self._get_alias_contact_description(),
            "default_email": default_email,
        }

    def _get_alias_contact_description(self) -> str:
        if self.alias_contact == "partners":
            return _("addresses linked to registered partners")
        if self.alias_contact == "followers":
            return _("followers of the related document")
        return _("some specific addresses")

    def _get_alias_invalid_body(self, message_dict: dict) -> Markup:
        self.check_singleton()
        self = self._alias_with_author_lang(message_dict)
        content = Markup(
            _(
                "The message below could not be accepted by the address "
                "%(alias_display_name)s. Please try again later or contact "
                "%(company_name)s instead."
            )
        ) % {
            "alias_display_name": self.display_name,
            "company_name": self._alias_get_company().name,
        }
        return self._alias_bounce_render(self._alias_bounce_wrap(content), message_dict)

    def _alias_get_bounce_body(
        self, message_dict: dict, is_config_error: bool = True
    ) -> Markup:
        self.check_singleton()
        if is_config_error:
            return self._get_alias_invalid_body(message_dict)
        return self._get_alias_bounced_body(message_dict)
