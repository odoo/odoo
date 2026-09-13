import re
import typing
from collections.abc import Callable
from typing import Any, Literal, Self

from odoo import Command, api, fields, models, tools
from odoo.api import DomainType, ValuesType
from odoo.exceptions import AccessError, MissingError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools.misc import limited_field_access_token

from odoo.addons.mail.tools.discuss import Store, StoreFieldsInput, StoreFieldSpec

if typing.TYPE_CHECKING:
    from odoo.addons.bus.models.res_users import ResUsers

_debug = DebugLog(__name__)

ROOT_EMAIL_UNIQUENESS_FIELDS = frozenset({"email", "active"})


class ResPartner(models.Model):
    _name = "res.partner"
    _inherit = [
        "res.partner",
        "mixin.mail.activity",
        "mixin.mail.presence",
        "mixin.mail.thread.blacklist",
    ]
    _mail_flat_thread = False

    name = fields.Char(tracking=1)
    email = fields.Char(tracking=1)
    phone_ids = fields.Many2many(tracking=2)
    parent_id: ResPartner = fields.Many2one(tracking=3)
    user_id: ResUsers = fields.Many2one(tracking=4)
    vat = fields.Char(tracking=5)
    contact_address_inline = fields.Char(
        string="Inlined Complete Address",
        compute="_compute_contact_address_inline",
        tracking=True,
    )

    @api.depends("contact_address")
    def _compute_contact_address_inline(self) -> None:
        for partner in self:
            partner.contact_address_inline = (
                re.sub(r"\n(\s|\n)*", ", ", partner.contact_address).strip().strip(",")
            )

    @api.depends("user_ids.manual_im_status", "user_ids.presence_ids.status")
    def _compute_presence(self) -> None:
        for partner in self:
            partner.im_status = (
                partner.user_ids.presence_ids._fold_im_status()
                if partner.user_ids
                else "im_partner"
            )
            partner.offline_since = (
                max(partner.user_ids.presence_ids.mapped("last_poll"), default=None)
                if partner.im_status == "offline"
                else None
            )
        odoobot_id = self.env["ir.model.data"]._xmlid_to_res_id("base.partner_root")
        odoobot = self.env["res.partner"].browse(odoobot_id)
        if odoobot in self:
            odoobot.im_status = "bot"

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        partners = super().create(vals_list)
        if partners._mail_shares_root_email():
            _debug.lifecycle("root_email_uniqueness_invalidated", by="create")
            self._mail_invalidate_root_email_uniqueness()
        return partners

    def write(self, vals: ValuesType) -> Literal[True]:
        watched = bool(vals.keys() & ROOT_EMAIL_UNIQUENESS_FIELDS)
        shared_before = watched and self._mail_shares_root_email()
        result = super().write(vals)
        if (
            shared_before
            or (watched and self._mail_shares_root_email())
            or ("email" in vals and self._mail_get_root_partner_id() in self._ids)
        ):
            _debug.lifecycle("root_email_uniqueness_invalidated", by="write")
            self._mail_invalidate_root_email_uniqueness()
        return result

    def unlink(self) -> Literal[True]:
        shared_before = self._mail_shares_root_email()
        result = super().unlink()
        if shared_before:
            self._mail_invalidate_root_email_uniqueness()
        return result

    @api.model
    def _mail_get_root_partner_id(self) -> int:
        return self.env["ir.model.data"]._xmlid_to_res_id("base.partner_root")

    @api.model
    @tools.ormcache(cache="stable")
    def _mail_get_root_email(self) -> str | Literal[False]:
        return self.browse(self._mail_get_root_partner_id()).sudo().email_normalized

    def _mail_shares_root_email(self) -> bool:
        root_email = self._mail_get_root_email()
        if not root_email:
            return False
        partners = self.sudo()
        try:
            return any(partner.email_normalized == root_email for partner in partners)
        except MissingError:
            return any(
                partner.email_normalized == root_email for partner in partners.exists()
            )

    @api.model
    @tools.ormcache("root_email", cache="stable")
    def _mail_root_email_is_unique(self, root_email: str) -> bool:
        return not (
            self.sudo()
            .with_context(active_test=True)
            .search_count(
                [
                    ("email_normalized", "=", root_email),
                    ("id", "!=", self._mail_get_root_partner_id()),
                ],
                limit=1,
            )
        )

    @api.model
    def _mail_invalidate_root_email_uniqueness(self) -> None:
        self.env.registry.clear_cache("stable")

    def _get_needaction_count(self) -> int:
        self.check_singleton()
        self.env["mail.notification"].flush_model(["is_read", "res_partner_id"])
        self.env.cr.execute(
            """
            SELECT count(*) as needaction_count
            FROM mail_notification R
            WHERE R.res_partner_id = %s AND (R.is_read = false OR R.is_read IS NULL)""",
            (self.id,),
        )
        return self.env.cr.dictfetchall()[0].get("needaction_count")

    def _mail_get_partners(self, introspect_fields: bool = False) -> dict:
        return {partner.id: partner for partner in self}

    @api.model
    def _get_view_cache_key(
        self, view_id: int | None = None, view_type: str = "form", **options
    ) -> tuple:
        key = super()._get_view_cache_key(view_id, view_type, **options)
        return key + (self.env.context.get("force_email"),)

    @api.model
    def get_or_create(self, email: str, assert_valid_email: bool = False) -> Self:
        if not email:
            raise ValueError("An email is required for get_or_create to work")

        parsed_name, parsed_email_normalized = tools.parse_contact_from_email(email)
        parsed_name = parsed_name.strip()
        if not parsed_email_normalized and assert_valid_email:
            raise ValueError(
                f"{email} is not recognized as a valid email. This is required "
                f"to create a new customer."
            )
        if parsed_email_normalized:
            partners = self.with_context(active_test=False).search(
                [("email_normalized", "=", parsed_email_normalized)],
                order=f"active DESC, {self._order}",
                limit=1,
            )
            if partners:
                _debug.logic("get_or_create", partner=partners.id, by="found")
                return partners

        create_values = {self._rec_name: parsed_name or parsed_email_normalized}
        if parsed_email_normalized:
            create_values["email"] = parsed_email_normalized
        _debug.lifecycle(
            "get_or_create", by="created", valid_email=bool(parsed_email_normalized)
        )
        return self.create(create_values)

    @api.model
    def _get_or_create_from_emails(
        self,
        emails: list[str],
        ban_emails: list[str] | None = None,
        filter_found: Callable[[Self], bool] | None = None,
        additional_values: dict | None = None,
        no_create: bool = False,
        sort_key: Callable[[Self], Any] | None = None,
        sort_reverse: bool = True,
    ) -> list:
        additional_values = additional_values or {}
        ban_emails = ban_emails or []
        partners, tocreate_vals_list = self.env["res.partner"], []
        name_emails = [
            (name.strip(), email_normalized)
            for name, email_normalized in (
                tools.parse_contact_from_email(email) for email in emails
            )
        ]

        emails_normalized = {
            email_normalized
            for _name, email_normalized in name_emails
            if email_normalized and email_normalized not in ban_emails
        }
        names = {
            name
            for name, email_normalized in name_emails
            if not email_normalized and name and name not in ban_emails
        }
        if emails_normalized or names:
            domains = []
            if emails_normalized:
                domains.append([("email_normalized", "in", list(emails_normalized))])
            if names:
                domains.append([("email", "in", list(names))])
            partners += self.with_context(active_test=False).search(
                Domain.OR(domains), order="active DESC, id ASC"
            )
            if filter_found:
                partners = partners.filtered(filter_found)
            if no_create:
                partners = partners.filtered("active")

        if not no_create:
            notfound_emails = emails_normalized - set(
                partners.mapped("email_normalized")
            )
            name_by_notfound_email = {}
            for name, email_normalized in name_emails:
                if email_normalized in notfound_emails:
                    name_by_notfound_email.setdefault(email_normalized, name)
            tocreate_vals_list += [
                {
                    self._rec_name: name or email_normalized,
                    "email": email_normalized,
                    **additional_values.get(email_normalized, {}),
                }
                for email_normalized, name in name_by_notfound_email.items()
            ]
            found_emails = set(partners.mapped("email"))
            tocreate_vals_list += [
                {
                    self._rec_name: name,
                    "email": name,
                    **additional_values.get(name, {}),
                }
                for name in names
                if name not in found_emails
            ]
            if tocreate_vals_list:
                partners += self.with_context(mail_create_nosubscribe=True).create(
                    [self._phone_vals_to_commands(vals) for vals in tocreate_vals_list]
                )

        if sort_key:
            partners = partners.sorted(key=sort_key, reverse=sort_reverse)

        _debug.logic(
            "partners_from_emails",
            emails=len(emails),
            normalized=len(emails_normalized),
            names=len(names),
            banned=len(ban_emails),
            found=len(partners) - len(tocreate_vals_list),
            created=len(tocreate_vals_list),
            no_create=no_create,
        )
        return self._get_partner_per_email(name_emails, emails, partners)

    @api.model
    def _phone_vals_to_commands(self, vals: dict) -> dict:
        commands = [
            Command.create({"number": number, "type": phone_type})
            for key, phone_type in (("phone", "landline"), ("mobile", "mobile"))
            if (number := vals.pop(key, False))
        ]
        if commands:
            vals["phone_ids"] = vals.get("phone_ids", []) + commands
        return vals

    @api.model
    def _get_or_create_from_emails_key(self, email: str) -> str:
        name, email_normalized = tools.parse_contact_from_email(email)
        return email_normalized or name.strip()

    def _get_partner_per_email(
        self,
        name_emails: list[tuple[str, str]],
        emails: list[str],
        partners: Self,
    ) -> list:
        empty = self.env["res.partner"]
        by_email_normalized, by_email, by_name = {}, {}, {}
        for partner in partners:
            by_email_normalized.setdefault(partner.email_normalized, partner)
            by_email.setdefault(partner.email, partner)
            by_name.setdefault(partner.name, partner)
        return [
            by_email_normalized.get(email_normalized, empty)
            if email_normalized
            else (
                (email and by_email.get(email)) or (name and by_name.get(name)) or empty
            )
            for (name, email_normalized), email in zip(name_emails, emails, strict=True)
        ]

    def _get_mention_token(self) -> str:
        self.check_singleton()
        return limited_field_access_token(self, "id", scope="mail.message_mention")

    def _get_fields_store_mention(self) -> list[StoreFieldSpec]:
        return [Store.Attr("mention_token", lambda p: p._get_mention_token())]

    def _get_fields_store_avatar_card(
        self, target: Store.Target
    ) -> list[StoreFieldSpec]:
        fields = [
            "im_status",
            "name",
            "partner_share",
        ]
        if target.is_internal(self.env):
            fields.extend(
                ["email", Store.Attr("phone", lambda p: p._phone_get_number().number)]
            )
        return fields

    def _to_store_defaults(self, target: Store.Target) -> StoreFieldsInput:
        res = [
            "active",
            "avatar_128",
            "im_status",
            "is_company",
            Store.One("main_user_id", ["partner_id", "share"], sudo=True),
            "name",
        ]
        if target.is_internal(self.env):
            res.append("email")
        return res

    @api.readonly
    @api.model
    def get_mention_suggestions(self, search: str, limit: int = 8) -> dict:
        domain = self._get_domain_mention_suggestions(search)
        partners = self._search_mention_suggestions(domain, limit)
        store = Store().add(partners, extra_fields=partners._get_fields_store_mention())
        try:
            roles = self.env["res.role"].search([("name", "ilike", search)], limit=8)
            store.add(roles, "name")
        except AccessError:
            pass
        return store.get_result()

    @api.model
    def _get_domain_mention_suggestions(self, search: str) -> Domain:
        return (
            Domain("name", "ilike", search) | Domain("email", "ilike", search)
        ) & Domain("active", "=", True)

    @api.model
    def _search_mention_suggestions(
        self, domain: DomainType, limit: int, extra_domain: DomainType | None = None
    ) -> Self:
        domain = Domain(domain)
        domain_is_user = (
            Domain("user_ids", "!=", False)
            & Domain("user_ids.active", "=", True)
            & domain
        )
        priority_conditions = [
            domain_is_user & Domain("partner_share", "=", False),
            domain_is_user,
            domain,
        ]
        if extra_domain:
            priority_conditions.append(Domain(extra_domain))
        partners = self.env["res.partner"]
        for domain in priority_conditions:
            remaining_limit = limit - len(partners)
            if remaining_limit <= 0:
                break
            query = self._search(
                Domain("id", "not in", partners.ids) & domain, limit=remaining_limit
            )
            partners |= self.browse(query)
        return partners

    @api.model
    def _get_current_persona(self) -> tuple:
        if not self.env.user or self.env.user._is_public():
            return (
                self.env["res.partner"],
                self.env["mail.guest"]._get_guest_from_context(),
            )
        return (self.env.user.partner_id, self.env["mail.guest"])


class ResPartnerTag(models.Model):
    _inherit = "res.partner.tag"

    _mail_partner_fields = ()
