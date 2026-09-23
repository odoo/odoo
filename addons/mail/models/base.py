import logging
import typing
from collections import defaultdict
from collections.abc import Callable, Collection, Iterable
from email.message import EmailMessage
from typing import Any, Literal, Self, TypedDict

from lxml import etree
from lxml.builder import E
from markupsafe import Markup

from odoo import api, exceptions, fields, models, tools
from odoo.db.schema import column_exists
from odoo.libs.debug_log import DebugLog
from odoo.tools import parse_contact_from_email
from odoo.tools.mail import (
    email_split_and_format,
    email_split_and_format_normalize,
)

from odoo.addons.base.models.ir_model_common import MODULE_UNINSTALL_FLAG
from odoo.addons.mail.tools.alias_error import AliasError
from odoo.addons.mail.tools.default_recipients import choose_default_recipients
from odoo.addons.mail.tools.discuss import Store, StoreFieldsInput, StoreFieldSpec
from odoo.addons.mail.tools.email_keys import (
    dedupe_emails_by_key,
    email_comparison_key,
)

if typing.TYPE_CHECKING:
    from odoo.addons.base.models.res_users import ResUsers
    from odoo.addons.mail.models.mail_alias import MailAlias
    from odoo.addons.mail.models.mail_alias_domain import MailAliasDomain
    from odoo.addons.mail.models.mail_message import MailMessage
    from odoo.addons.mail.models.mail_message_subtype import MailMessageSubtype
    from odoo.addons.mail.models.res_company import ResCompany
    from odoo.addons.mail.models.res_partner import ResPartner

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


class RecipientSources(TypedDict):
    email_cc_lst: list[str]
    email_to_lst: list[str]
    partners: ResPartner


class SuggestionSources(TypedDict):
    email_to_lst: list[str]
    partners: ResPartner


class DefaultRecipients(TypedDict):
    email_cc: str
    email_to: str
    partner_ids: list[int]


class SuggestedRecipient(TypedDict, total=False):
    display_name: str
    email: str | Literal[False]
    name: str | Literal[False]
    partner_id: int | Literal[False]
    create_values: dict


_MAIL_EMAIL_FIELD_TYPES = ("char", "text")

_MAIL_TIMEZONE_FIELD_TYPES = ("selection", "char")

_MAIL_REPLY_TO_LENGTH_LIMIT = 68


class Base(models.AbstractModel):
    _inherit = "base"
    _mail_defaults_to_email = False
    _mail_post_access = "write"
    _primary_email = None
    _partner_unfollow_enabled = False
    _mail_partner_fields = None
    _mail_default_email_fields = (
        "email_from",
        "x_email_from",
        "email",
        "x_email",
        "partner_email",
        "email_normalized",
    )
    _mail_default_email_cc_fields = ("email_cc", "partner_email_cc", "x_email_cc")
    _mail_default_timezone_fields = ("date_tz", "tz", "timezone")

    def _is_valid_field_parameter(self, field: fields.Field, name: str) -> bool:
        return (
            name == "tracking" and self._abstract
        ) or super()._is_valid_field_parameter(field, name)

    @api.model
    @tools.ormcache()
    def _display_name_field_names(self) -> frozenset[str]:
        field_depends = self.env.registry.field_depends
        roots: set[str] = set()
        expanded: set[fields.Field] = set()
        todo = [self._fields["display_name"]]
        while todo:
            field = todo.pop()
            if field in expanded:
                continue
            expanded.add(field)
            for dependency in field_depends[field]:
                root, _sep, path = dependency.partition(".")
                roots.add(root)
                dependency_field = self._fields.get(root)
                if (
                    dependency_field is not None
                    and dependency_field.compute
                    and not path
                ):
                    todo.append(dependency_field)
        return frozenset(roots)

    def with_user(self, user: ResUsers | int) -> Self:
        records = super().with_user(user)
        if "guest" not in records.env.context:
            return records
        context = {k: v for k, v in records.env.context.items() if k != "guest"}
        return records.with_env(records.env(context=context))

    def unlink(self) -> Literal[True]:
        record_ids = self.ids if (not self._abstract and not self._transient) else []
        result = super().unlink()
        if record_ids and (
            not self.env.context.get(MODULE_UNINSTALL_FLAG)
            or (
                column_exists(self.env.cr, "mail_activity", "res_model")
                and column_exists(self.env.cr, "mail_activity", "res_id")
            )
        ):
            self._mail_unlink_activities(record_ids)
        return result

    def _mail_unlink_activities(self, record_ids: list[int]) -> None:
        activities = (
            self.env["mail.activity"]
            .with_context(active_test=False)
            .sudo()
            .search([("res_model", "=", self._name), ("res_id", "in", record_ids)])
        )
        if not activities:
            return
        _debug.lifecycle(
            "activities_unlinked_with_records",
            model=self._name,
            records=len(record_ids),
            activities=len(activities),
        )
        activities.unlink()

    def _to_store_defaults(self, target: Store.Target) -> StoreFieldsInput:
        return []

    def _field_store_repr(self, field_spec: StoreFieldSpec) -> list[StoreFieldSpec]:
        return [field_spec]

    def _to_store(
        self, store: Store, field_specs: list[StoreFieldSpec], **kwargs
    ) -> None:
        if kwargs:
            raise TypeError(
                f"unexpected _to_store parameters for {self._name}: {kwargs}"
            )
        store.add_records_fields(self, field_specs)

    def _thread_to_store(
        self, store: Store, field_specs: list[StoreFieldSpec], **kwargs
    ) -> None:
        if kwargs:
            raise TypeError(
                f"unexpected _thread_to_store parameters for {self._name}: {kwargs}"
            )
        store.add_records_fields(self, field_specs, as_thread=True)

    def _mail_get_followers(self) -> dict[int, ResPartner]:
        return dict.fromkeys(self._ids, self.env["res.partner"])

    def _mail_get_thread_messages(self) -> dict[int, MailMessage]:
        return dict.fromkeys(self._ids, self.env["mail.message"])

    def _creation_subtype(self) -> MailMessageSubtype:
        return self.env["mail.message.subtype"]

    def _mail_get_customer_information(self) -> dict[str, dict]:
        return {}

    def _mail_get_operation_for_mail_message_operation(
        self, message_operation: str
    ) -> dict[models.Model, str]:
        valid_operations = {"read", "write", "unlink", "create"}
        if message_operation not in valid_operations:
            raise ValueError(
                "Invalid message operation, should be a valid ORM operation type"
            )
        if self._mail_post_access not in valid_operations:
            raise ValueError(
                "Invalid _mail_post_access, should be a valid ORM operation type"
            )

        if message_operation == "read":
            check_access = "read"
        elif message_operation == "create":
            check_access = self._mail_post_access
        else:
            check_access = "write"
        return dict.fromkeys(self, check_access)

    def _mail_group_by_operation_for_mail_message_operation(
        self, message_operation: str
    ) -> dict[str, models.Model]:
        document_operations = self._mail_get_operation_for_mail_message_operation(
            message_operation
        )
        self_ids = set(self._ids)
        documents = self.browse(
            record.id
            for record, operation in document_operations.items()
            if operation and record.id in self_ids
        ).with_prefetch(self._prefetch_ids)
        return documents.grouped(document_operations.__getitem__)

    def _mail_get_alias_domains(
        self, default_company: ResCompany | Literal[False] = False
    ) -> dict[int, MailAliasDomain]:
        fallback_company = default_company or self.env.company
        record_companies = self._mail_get_companies(default=fallback_company)

        default_domain = fallback_company.alias_domain_id
        all_companies = self.env["res.company"].browse(
            {comp.id for comp in record_companies.values()}
        )
        if not default_domain and any(
            not comp.alias_domain_id for comp in all_companies
        ):
            default_domain = self.env["mail.alias.domain"]._get_default_domain()

        return {
            record.id: (record_companies[record.id].alias_domain_id or default_domain)
            for record in self
        }

    @api.model
    def _mail_get_company_field(self) -> str | Literal[False]:
        field = self._fields.get("company_id")
        if field and field.type == "many2one" and field.comodel_name == "res.company":
            return "company_id"
        return False

    def _mail_get_companies(
        self, default: ResCompany | Literal[False] = False
    ) -> dict[int, ResCompany]:
        default_company = default or self.env["res.company"]
        company_fname = self._mail_get_company_field()
        return {
            record.id: (record[company_fname] or default_company)
            if company_fname
            else default_company
            for record in self
        }

    def _mail_get_customer(self, introspect_fields: bool = False) -> ResPartner:
        self.check_singleton()
        customers = self._mail_get_partners(introspect_fields=introspect_fields)[
            self.id
        ]
        return customers[0] if customers else self.env["res.partner"]

    @api.model
    def _mail_is_partner_field(self, fname: str) -> bool:
        field = self._fields.get(fname)
        return bool(
            field
            and field.type in ("many2one", "many2many", "one2many")
            and field.comodel_name == "res.partner"
        )

    @api.model
    @tools.ormcache()
    def _mail_declared_partner_fields(self) -> tuple[str, ...]:
        declared = tuple(self._mail_partner_fields or ())
        valid = tuple(fname for fname in declared if self._mail_is_partner_field(fname))
        if invalid := [fname for fname in declared if fname not in valid]:
            _logger.warning(
                "%s._mail_partner_fields names %s, which is not a relation to "
                "res.partner; ignored.",
                self._name,
                ", ".join(repr(fname) for fname in invalid),
            )
        return valid

    def _mail_get_partner_fields(self, introspect_fields: bool = False) -> list[str]:
        if self._mail_partner_fields is not None:
            return list(self._mail_declared_partner_fields())
        partner_fnames = [
            fname
            for fname in ("partner_id", "partner_ids")
            if (field := self._fields.get(fname))
            and field.type in ("many2one", "many2many")
            and field.comodel_name == "res.partner"
        ]
        if not partner_fnames and introspect_fields:
            partner_fnames = [
                fname
                for fname, fvalue in self._fields.items()
                if fvalue.type == "many2one" and fvalue.comodel_name == "res.partner"
            ]
        return partner_fnames

    @api.model
    @api.readonly
    def mail_get_partner_fields(self) -> list[str]:
        return [
            fname
            for fname in self._mail_get_partner_fields()
            if (field := self._fields.get(fname)) and field.type == "many2one"
        ]

    def _mail_get_partners(
        self, introspect_fields: bool = False
    ) -> dict[int, ResPartner]:
        partner_fields = self._mail_get_partner_fields(
            introspect_fields=introspect_fields
        )
        pids_per_record = {
            record.id: list(
                tools.unique(pid for fn in partner_fields for pid in record[fn].ids)
            )
            for record in self
        }
        all_pids = {pid for pids in pids_per_record.values() for pid in pids}
        return {
            res_id: self.env["res.partner"].browse(pids).with_prefetch(all_pids)
            for res_id, pids in pids_per_record.items()
        }

    @api.model
    def _mail_get_primary_email_field(self) -> str | None:
        if not isinstance(self._primary_email, str):
            return None
        field = self._fields.get(self._primary_email)
        if field is not None and field.type in _MAIL_EMAIL_FIELD_TYPES:
            return self._primary_email
        return None

    def _mail_get_primary_email(self) -> dict[int, str | Literal[False]]:
        fname = self._mail_get_primary_email_field()
        return {record.id: record[fname] if fname else False for record in self}

    @api.model
    @api.readonly
    def mail_allowed_qweb_expressions(self) -> tuple[str, ...]:
        return (
            "object.name",
            "object.contact_name",
            "object.partner_id",
            "object.partner_id.name",
            "object.user_id",
            "object.user_id.name",
            "object.user_id.signature",
        )

    def _mail_track(
        self, tracked_fields: dict[str, dict], initial_values: dict[str, Any]
    ) -> tuple[set[str], list[list]]:
        self.check_singleton()
        updated = set()
        tracking_value_ids = []

        fields_track_info = self._mail_track_order_fields(tracked_fields)
        for col_name, _sequence in fields_track_info:
            if col_name not in initial_values:
                continue
            initial_value = initial_values[col_name]
            new_value = (
                field.convert_to_read(self[col_name], self)
                if (field := self._fields[col_name]).type == "properties"
                else self[col_name]
            )
            if new_value == initial_value or (not new_value and not initial_value):
                continue

            if field.type == "properties":
                definition_record_field = field.definition_record
                if self[definition_record_field] == initial_values.get(
                    definition_record_field, self[definition_record_field]
                ):
                    continue

                updated.add(col_name)
                tracking_value_ids.extend(
                    [
                        0,
                        0,
                        self.env[
                            "mail.tracking.value"
                        ]._prepare_tracking_values_property(
                            property_,
                            col_name,
                            tracked_fields[col_name],
                            self,
                            definition_index=definition_index,
                        ),
                    ]
                    for definition_index, property_ in reversed(
                        list(enumerate(initial_value))
                    )
                    if property_["type"] not in ("separator", "html")
                    and property_.get("value")
                )
                continue

            updated.add(col_name)
            tracking_value_ids.append(
                [
                    0,
                    0,
                    self.env["mail.tracking.value"]._prepare_tracking_values(
                        initial_value,
                        new_value,
                        col_name,
                        tracked_fields[col_name],
                        self,
                    ),
                ]
            )

        if _debug.logic.enabled and updated:
            _debug.logic(
                "tracked",
                model=self._name,
                record=self.id,
                fields=sorted(updated),
                values=len(tracking_value_ids),
            )
        return updated, tracking_value_ids

    def _mail_track_field_sequences(
        self, tracked_fields: dict[str, dict]
    ) -> dict[str, int]:
        return {
            col_name: self._mail_track_get_field_sequence(col_name)
            for col_name in tracked_fields
        }

    def _mail_track_order_fields(
        self, tracked_fields: dict[str, dict]
    ) -> list[tuple[str, int]]:
        fields_track_info = list(
            self._mail_track_field_sequences(tracked_fields).items()
        )
        fields_track_info.sort(
            key=lambda item: (
                item[1],
                tracked_fields[item[0]]["type"] == "properties",
                item[0],
            ),
            reverse=True,
        )
        return fields_track_info

    def _mail_track_get_field_sequence(self, fname: str) -> int:
        if fname not in self._fields:
            return 100

        def get_field_sequence(fname: str) -> int:
            return getattr(self._fields[fname], "tracking", True)

        sequence = get_field_sequence(fname)
        if self._fields[fname].type == "properties" and sequence is True:
            parent_sequence = get_field_sequence(self._fields[fname].definition_record)
            return 100 if parent_sequence is True else parent_sequence
        return 100 if sequence is True else sequence

    def _message_get_default_recipients_sources(self) -> dict[int, RecipientSources]:
        res = {}
        customers = self._mail_get_partners()
        primary_emails = self._mail_get_primary_email()
        for record in self:
            email_cc_lst, email_to_lst = [], []
            recipients_all = customers[record.id]
            email_to = primary_emails[record.id] or record._mail_get_email_value(
                self._mail_default_email_fields
            )
            if email_to:
                email_to_lst = email_split_and_format_normalize(email_to) or [email_to]
            email_cc = record._mail_get_email_value(self._mail_default_email_cc_fields)
            if email_cc:
                email_cc_lst = email_split_and_format_normalize(email_cc) or [email_cc]

            res[record.id] = {
                "email_cc_lst": email_cc_lst,
                "email_to_lst": email_to_lst,
                "partners": recipients_all,
            }
        return res

    def _mail_first_field_value(
        self, fnames: Iterable[str], field_types: Collection[str]
    ) -> Any:
        self.check_singleton()
        return next(
            (
                self[fname]
                for fname in fnames
                if (field := self._fields.get(fname))
                and field.type in field_types
                and self[fname]
            ),
            None,
        )

    def _mail_get_email_value(self, fnames: Iterable[str]) -> str | Literal[False]:
        return self._mail_first_field_value(fnames, _MAIL_EMAIL_FIELD_TYPES) or False

    def _mail_get_banned_emails(self, emails: Iterable[str]) -> set[str]:
        keys = list(
            tools.unique(email_comparison_key(e) for e in emails if e and e.strip())
        )
        Partner = self.env["res.partner"]
        root_email = Partner._mail_get_root_email()
        banned = set()
        if (
            root_email
            and root_email in keys
            and Partner._mail_root_email_is_unique(root_email)
        ):
            banned.add(root_email)
        banned.update(
            alias
            for alias in self.env["mail.alias.domain"].sudo()._get_alias_emails(keys)
            if alias
        )
        return banned

    def _message_get_default_recipients(
        self, with_cc: bool = False
    ) -> dict[int, DefaultRecipients]:
        res = {}
        prioritize_email = self._mail_defaults_to_email
        found = self._message_get_default_recipients_sources()

        all_emails = []
        for defaults in found.values():
            all_emails += defaults["email_to_lst"]
            if with_cc:
                all_emails += defaults["email_cc_lst"]
            all_emails += defaults["partners"].mapped("email_normalized")
        ban_emails = self._mail_get_banned_emails(all_emails)

        for record in self:
            defaults = found[record.id]
            customers = defaults["partners"]
            email_cc_lst = defaults["email_cc_lst"] if with_cc else []
            email_to_lst = defaults["email_to_lst"]
            keep_ids, mailable_ids = [], []
            for partner in customers:
                if partner.is_public:
                    continue
                email_normalized = partner.email_normalized
                if not email_normalized:
                    keep_ids.append(partner.id)
                elif email_normalized not in ban_emails:
                    keep_ids.append(partner.id)
                    mailable_ids.append(partner.id)
            recipients_all = customers.browse(keep_ids).with_prefetch(customers._ids)
            recipients = customers.browse(mailable_ids).with_prefetch(customers._ids)
            email_cc_lst = [
                e for e in email_cc_lst if email_comparison_key(e) not in ban_emails
            ]
            email_to_lst = [
                e for e in email_to_lst if email_comparison_key(e) not in ban_emails
            ]
            partner_ids, email_to = choose_default_recipients(
                prioritize_email=prioritize_email,
                email_to_lst=email_to_lst,
                to_keys=[email_comparison_key(email) for email in email_to_lst],
                mailable_ids=recipients.ids,
                mailable_keys=set(recipients.mapped("email_normalized")),
                kept_ids=recipients_all.ids,
                kept_keys={
                    email_comparison_key(email)
                    for email in recipients_all.mapped("email")
                },
            )
            res[record.id] = {
                "email_cc": ",".join(email_cc_lst),
                "email_to": email_to,
                "partner_ids": partner_ids,
            }
        _debug.logic(
            "default_recipients",
            model=self._name,
            records=len(self),
            prioritize_email=prioritize_email,
            with_cc=with_cc,
            banned=len(ban_emails),
        )
        return res

    def _message_get_suggested_recipients_sources(
        self, force_primary_email: str | Literal[False] = False
    ) -> dict[int, SuggestionSources]:
        suggested = {
            record.id: {"email_to_lst": [], "partners": self.env["res.partner"]}
            for record in self
        }
        defaults = self._message_get_default_recipients_sources()
        user_field = self._fields.get("user_id")
        if (
            user_field
            and user_field.type == "many2one"
            and user_field.comodel_name == "res.users"
        ):
            for record_su in self.sudo():
                if record_su.user_id.partner_id == self.env.user.partner_id:
                    continue
                suggested[record_su.id]["partners"] += record_su.user_id.partner_id
        for record_id, values in defaults.items():
            suggested[record_id]["partners"] |= values["partners"]

        for record in self:
            if force_primary_email:
                suggested[record.id]["email_to_lst"] += (
                    email_split_and_format_normalize(force_primary_email)
                )
            else:
                suggested[record.id]["email_to_lst"] += defaults[record.id][
                    "email_to_lst"
                ]

        return suggested

    def _message_get_suggested_recipients_batch(
        self,
        reply_discussion: bool = False,
        reply_message: MailMessage | None = None,
        no_create: bool = True,
        primary_email: str | Literal[False] = False,
        additional_partners: ResPartner | None = None,
    ) -> dict[int, list[SuggestedRecipient]]:
        sources = self._message_get_suggested_recipients_sources(
            force_primary_email=primary_email
        )
        suggested = self._message_add_suggested_recipients_from_replies(
            self._message_suggested_recipients_candidates(sources, additional_partners),
            reply_discussion=reply_discussion,
            reply_message=reply_message,
        )
        suggested = self._message_suggested_recipients_readable(suggested)

        followers_by_record = self._mail_get_followers()
        customer_information = self._mail_get_customer_information_batch()

        partner_ids = {
            pid for vals in suggested.values() for pid in vals["partners"]._ids
        } | {pid for recs in followers_by_record.values() for pid in recs._ids}

        email_keys: dict[Any, set[str]] = {}
        records_emails, all_emails = self._message_suggested_recipients_emails(
            suggested, followers_by_record, partner_ids, email_keys
        )
        ban_emails = self._mail_get_banned_emails(all_emails)
        records_partners = self._partner_get_or_create_from_emails(
            records_emails,
            avoid_alias=False,
            ban_emails=list(ban_emails),
            no_create=no_create,
            customer_information=customer_information,
        )
        partner_ids |= {pid for recs in records_partners.values() for pid in recs._ids}
        _debug.pipeline(
            "suggested_recipients",
            model=self._name,
            records=len(self),
            reply_discussion=reply_discussion,
            reply_message=reply_message.id if reply_message else None,
            no_create=no_create,
            partners=len(partner_ids),
            banned=len(ban_emails),
        )

        suggested_recipients = {}
        for record in self:
            followers = followers_by_record[record.id]
            partners = self._message_suggested_recipients_partners(
                suggested[record.id]["partners"] + records_partners[record.id],
                followers=followers,
                keep_followers=sources[record.id]["partners"],
                ban_emails=ban_emails,
                prefetch_ids=partner_ids,
            )
            suggested_recipients[record.id] = self._message_suggested_recipients_values(
                partners,
                self._message_suggested_emails(
                    suggested[record.id]["email_to_lst"],
                    skip_keys=ban_emails
                    | self._mail_get_email_keys_cached(
                        (followers | partners).with_prefetch(partner_ids), email_keys
                    ),
                ),
                customer_information,
            )
        return suggested_recipients

    def _message_suggested_recipients_candidates(
        self, sources: dict[int, SuggestionSources], additional_partners: ResPartner
    ) -> dict[int, SuggestionSources]:
        additional_partners = additional_partners or self.env["res.partner"]
        candidates = {
            record.id: {
                "email_to_lst": sources[record.id]["email_to_lst"].copy(),
                "partners": sources[record.id]["partners"] + additional_partners,
            }
            for record in self
        }
        return self._message_suggested_recipients_prefetch(candidates)

    def _message_suggested_recipients_prefetch(
        self, suggested: dict[int, SuggestionSources]
    ) -> dict[int, SuggestionSources]:
        prefetch_ids = {
            pid for vals in suggested.values() for pid in vals["partners"]._ids
        }
        return {
            res_id: {**vals, "partners": vals["partners"].with_prefetch(prefetch_ids)}
            for res_id, vals in suggested.items()
        }

    def _message_suggested_recipients_readable(
        self, suggested: dict[int, SuggestionSources]
    ) -> dict[int, SuggestionSources]:
        candidates = self.env["res.partner"].browse(
            {pid for vals in suggested.values() for pid in vals["partners"]._ids}
        )
        readable = set(candidates._filtered_access("read")._ids)
        if len(readable) == len(candidates):
            return suggested
        return self._message_suggested_recipients_prefetch(
            {
                res_id: {
                    **vals,
                    "partners": vals["partners"].filtered(
                        lambda partner: partner.id in readable
                    ),
                }
                for res_id, vals in suggested.items()
            }
        )

    def _message_suggested_recipients_emails(
        self,
        suggested: dict[int, SuggestionSources],
        followers_by_record: dict[int, ResPartner],
        prefetch_ids: set,
        email_keys: dict[Any, set[str]],
    ) -> tuple[dict[models.BaseModel, list[str]], set[str]]:
        records_emails, all_emails = {}, set()
        for record in self:
            partners = suggested[record.id]["partners"]
            skip_keys = self._mail_get_email_keys_cached(
                (followers_by_record[record.id] | partners).with_prefetch(prefetch_ids),
                email_keys,
            )
            records_emails[record] = [
                email
                for email_input in suggested[record.id]["email_to_lst"]
                for email in email_split_and_format(email_input)
                if email
                and email.strip()
                and email_comparison_key(email) not in skip_keys
            ]
            all_emails |= set(records_emails[record]) | set(
                partners.mapped("email_normalized")
            )
        return records_emails, all_emails

    def _message_suggested_recipients_partners(
        self,
        partners: ResPartner,
        followers: ResPartner,
        keep_followers: ResPartner,
        ban_emails: set,
        prefetch_ids: set,
    ) -> ResPartner:
        return (
            self.env["res.partner"]
            .browse(
                tools.unique(
                    partner.id
                    for partner in partners.with_prefetch(prefetch_ids)
                    if (
                        partner not in followers
                        or (partner in keep_followers and partner.partner_share)
                    )
                    and partner.email_normalized not in ban_emails
                    and not partner.is_public
                )
            )
            .with_prefetch(prefetch_ids)
        )

    @api.model
    def _mail_get_email_keys_cached(
        self, partners: ResPartner, cache: dict[Any, set[str]]
    ) -> set[str]:
        keys = set()
        for partner in partners:
            partner_keys = cache.get(partner.id)
            if partner_keys is None:
                partner_keys = cache[partner.id] = self._mail_get_email_keys(partner)
            keys |= partner_keys
        return keys

    @api.model
    def _mail_get_email_keys(self, partners: ResPartner) -> set[str]:
        keys = set()
        for partner in partners:
            if partner.email_normalized:
                keys.add(partner.email_normalized)
            keys.update(
                email_comparison_key(email)
                for email in email_split_and_format(partner.email or "")
            )
        return keys

    def _partner_get_or_create_from_emails_single(
        self,
        emails: list[str],
        avoid_alias: bool = True,
        ban_emails: list[str] | None = None,
        filter_found: Callable[[ResPartner], Any] | None = None,
        additional_values: dict[str, dict] | None = None,
        customer_information: dict[str, dict] | None = None,
        no_create: bool = False,
    ) -> ResPartner:
        if self:
            self.check_singleton()
        return self._partner_get_or_create_from_emails(
            {self: emails},
            avoid_alias=avoid_alias,
            ban_emails=ban_emails,
            filter_found=filter_found,
            additional_values=additional_values,
            customer_information=customer_information,
            no_create=no_create,
        )[self.id]

    def _partner_get_or_create_from_emails_records(
        self, records_emails: dict[models.BaseModel, list[str]]
    ) -> models.BaseModel:
        keys = list(records_emails)
        record_models = {record._name for record in keys}
        if len(record_models) > 1:
            raise ValueError(
                f"_partner_get_or_create_from_emails takes records of a single model, "
                f"got {sorted(record_models)}"
            )
        records = keys[0].union(*keys[1:]) if keys else self.browse()
        if self and set(self._ids) != set(records._ids):
            raise ValueError(
                f"_partner_get_or_create_from_emails: self must be empty or exactly the "
                f"records of records_emails, got {self} against {records}"
            )
        return records

    def _partner_get_or_create_from_emails_values(
        self,
        additional_values: dict[str, dict] | None = None,
        customer_information: dict[str, dict] | None = None,
    ) -> dict[str, dict]:
        values = (
            self._mail_get_customer_information_batch()
            if customer_information is None
            else {
                email_comparison_key(key): dict(vals)
                for key, vals in customer_information.items()
            }
        )
        for key, update in (additional_values or {}).items():
            values.setdefault(email_comparison_key(key), {}).update(update)
        return values

    def _partner_get_or_create_from_emails_sort_key(
        self, emails_key_company_id: dict[str, int | Literal[False]]
    ) -> Callable[[ResPartner], tuple[bool, ...]]:
        follower_ids = {
            partner.id
            for partners in self._mail_get_followers().values()
            for partner in partners
        }
        current_partner_id = self.env.user.partner_id.id

        def sort_key(p: ResPartner) -> tuple[bool, ...]:
            return (
                p.active,
                p.id == current_partner_id,
                p.id in follower_ids,
                not p.partner_share,
                bool(p.user_ids),
                p.company_id.id == emails_key_company_id.get(p.email_normalized, False),
                not p.company_id,
            )

        return sort_key

    def _partner_get_or_create_from_emails(
        self,
        records_emails: dict[models.BaseModel, list[str]],
        avoid_alias: bool = True,
        ban_emails: list[str] | None = None,
        filter_found: Callable[[ResPartner], Any] | None = None,
        additional_values: dict[str, dict] | None = None,
        customer_information: dict[str, dict] | None = None,
        no_create: bool = False,
    ) -> dict[int | Literal[False], ResPartner]:
        records = self._partner_get_or_create_from_emails_records(records_emails)
        res_ids = list(records._ids) or [record.id for record in records_emails]
        found_results = dict.fromkeys(res_ids, self.env["res.partner"])
        emails_all = []
        emails_key_all = []
        emails_key_company_id = {}
        emails_key_res_ids = defaultdict(list)

        records_company = records.sudo()._mail_get_companies()
        emails_normalized_info = records._partner_get_or_create_from_emails_values(
            additional_values=additional_values,
            customer_information=customer_information,
        )

        for record, mails in records_emails.items():
            record_company = records_company.get(record.id, self.env["res.company"])
            for mail in mails:
                email_key = email_comparison_key(mail)
                emails_key_res_ids[email_key].append(record.id)
                if record_company and email_key:
                    known_company_id = emails_key_company_id.get(
                        email_key, record_company.id
                    )
                    emails_key_company_id[email_key] = (
                        record_company.id
                        if known_company_id == record_company.id
                        else False
                    )
                emails_all.append(mail)
                emails_key_all.append(email_key)
        if not emails_all:
            return found_results
        _debug.logic(
            "partners_from_emails",
            model=self._name,
            records=len(res_ids),
            emails=len(emails_all),
            avoid_alias=avoid_alias,
            no_create=no_create,
            companies=len(emails_key_company_id),
        )

        alias_emails = (
            self.env["mail.alias.domain"].sudo()._get_alias_emails(emails_key_all)
            if avoid_alias
            else []
        )
        ban_emails = (ban_emails or []) + alias_emails
        sort_key = records._partner_get_or_create_from_emails_sort_key(
            emails_key_company_id
        )

        Partner = self.env["res.partner"]
        partners = Partner._get_or_create_from_emails(
            emails_all,
            additional_values={
                Partner._get_or_create_from_emails_key(mail): {
                    "company_id": emails_key_company_id.get(mail_key, False),
                    **emails_normalized_info.get(mail_key, {}),
                }
                for mail, mail_key in zip(emails_all, emails_key_all, strict=True)
            },
            ban_emails=ban_emails,
            filter_found=filter_found,
            no_create=no_create,
            sort_key=sort_key,
            sort_reverse=True,
        )

        for mail_key, partner in zip(emails_key_all, partners, strict=True):
            for res_id in emails_key_res_ids[mail_key]:
                found_results[res_id] |= partner
        _debug.perf.count(
            "partners_resolved",
            model=self._name,
            emails=len(emails_all),
            partners=len(partners),
            banned=len(ban_emails),
        )
        return found_results

    def _mail_get_customer_information_batch(self) -> dict[str, dict]:
        values = {}
        for record in self:
            for (
                email_key,
                record_values,
            ) in record._mail_get_customer_information().items():
                merged = values.setdefault(email_comparison_key(email_key), {})
                for key, value in record_values.items():
                    merged.setdefault(key, value)
        return values

    def _message_add_suggested_recipients_from_replies(
        self,
        suggested: dict[int, SuggestionSources],
        reply_discussion: bool = False,
        reply_message: MailMessage | None = None,
    ) -> dict[int, SuggestionSources]:
        sorted_messages = {}
        if reply_discussion:
            messages_by_record = self._mail_get_thread_messages()
            subtype_ids = self._mail_suggested_message_subtype_ids()
            sorted_messages = {
                record.id: record._sort_suggested_messages(
                    messages_by_record[record.id], subtype_ids
                )
                for record in self
            }
        if not reply_message and not any(sorted_messages.values()):
            return suggested
        suggested = {
            res_id: {**vals, "email_to_lst": list(vals["email_to_lst"])}
            for res_id, vals in suggested.items()
        }
        for record in self:
            record_msg = reply_message or next(
                iter(sorted_messages.get(record.id, self.env["mail.message"])),
                self.env["mail.message"],
            )
            if not record_msg:
                continue
            suggested[record.id]["partners"] += (
                record_msg.partner_ids | record_msg.author_id
            ).filtered(lambda partner: partner.active)
            suggested[record.id]["email_to_lst"] += [
                record_msg.incoming_email_to or "",
                record_msg.incoming_email_cc or "",
                record_msg.email_from or "",
            ]
        return self._message_suggested_recipients_prefetch(suggested)

    def _message_suggested_emails(
        self, email_to_lst: list[str], skip_keys: set[str]
    ) -> list[str]:
        return dedupe_emails_by_key(email_to_lst, skip_keys)

    def _message_suggested_recipients_values(
        self,
        partners: ResPartner,
        email_to_lst: list[str],
        emails_normalized_info: dict[str, dict],
    ) -> list[SuggestedRecipient]:
        recipients = [
            {
                **({"display_name": partner.display_name} if not partner.name else {}),
                "email": partner.email_normalized,
                "name": partner.name,
                "partner_id": partner.id,
                "create_values": {},
            }
            for partner in partners
        ]
        for email_input in email_to_lst:
            name, email_normalized = parse_contact_from_email(email_input)
            create_values = dict(emails_normalized_info.get(email_normalized, {}))
            recipients.append(
                {
                    "email": email_normalized,
                    "name": create_values.pop("name", False) or name,
                    "partner_id": False,
                    "create_values": create_values,
                }
            )
        return recipients

    def _sort_suggested_messages(
        self, messages: MailMessage, subtype_ids: Collection[int] | None = None
    ) -> MailMessage:
        if subtype_ids is None:
            subtype_ids = self._mail_suggested_message_subtype_ids()
        return (
            messages.filtered(
                lambda msg: (
                    msg.message_type in ("email", "comment")
                    and msg.subtype_id.id in subtype_ids
                )
            )
            .with_prefetch(messages._prefetch_ids)
            .sorted(lambda msg: (bool(msg.date), msg.date, msg.id), reverse=True)
        )

    def _mail_suggested_message_subtype_ids(self) -> list[int]:
        subtype_ids = self._creation_subtype().ids
        comment_subtype_id = self.env["ir.model.data"]._xmlid_to_res_id(
            "mail.mt_comment"
        )
        if comment_subtype_id:
            subtype_ids.append(comment_subtype_id)
        return subtype_ids

    def _message_get_suggested_recipients(
        self,
        reply_discussion: bool = False,
        reply_message: MailMessage | None = None,
        no_create: bool = True,
        primary_email: str | Literal[False] = False,
        additional_partners: ResPartner | None = None,
    ) -> list[SuggestedRecipient]:
        self.check_singleton()
        return self._message_get_suggested_recipients_batch(
            reply_discussion=reply_discussion,
            reply_message=reply_message,
            no_create=no_create,
            primary_email=primary_email,
            additional_partners=additional_partners,
        )[self.id]

    def _notify_get_reply_to(
        self,
        default: str | Literal[False] | None = None,
        author_id: int | Literal[False] = False,
    ) -> dict[int | Literal[False], str | Literal[False] | None]:
        keys = self._notify_reply_to_scope()[2]
        return self._notify_get_reply_to_batch(
            defaults=dict.fromkeys(keys, default),
            author_ids=dict.fromkeys(keys, author_id),
        )

    def _notify_reply_to_scope(self) -> tuple[str | Literal[False], list, list]:
        model = self._name if self and self._name != "mixin.mail.thread" else False
        res_ids = list(self._ids) if model else []
        return model, res_ids, res_ids or [False]

    def _notify_get_reply_to_addresses(
        self,
    ) -> dict[int | Literal[False], str]:
        model, res_ids, _res_ids = self._notify_reply_to_scope()

        if res_ids:
            company_to_res_ids = defaultdict(list)
            for record_id, company in (
                self.sudo()._mail_get_companies(default=self.env.company).items()
            ):
                company_to_res_ids[company].append(record_id)
        else:
            company_to_res_ids = {self.env.company: _res_ids}

        reply_to_email = {}
        if model and res_ids:
            by_parent = self.env["mail.alias"]._get_alias_addresses().by_parent
            for record in self:
                if record._origin and (
                    address := by_parent.get((model, record._origin.id))
                ):
                    reply_to_email[record.id] = address

        by_alias = len(reply_to_email)  # debuglog
        if set(_res_ids) - set(reply_to_email):
            for company, record_ids in company_to_res_ids.items():
                if not company.catchall_email:
                    continue
                left_ids = set(record_ids) - set(reply_to_email)
                if left_ids:
                    reply_to_email.update(
                        dict.fromkeys(left_ids, company.catchall_email)
                    )
        _debug.logic(
            "reply_to_addresses",
            model=model or None,
            records=len(_res_ids),
            by_alias=by_alias,
            by_catchall=len(reply_to_email) - by_alias,
            companies=len(company_to_res_ids),
        )
        return reply_to_email

    def _notify_get_reply_to_batch(
        self,
        defaults: dict[int | Literal[False], str | Literal[False] | None] | None = None,
        author_ids: dict[int | Literal[False], int | Literal[False]] | None = None,
    ) -> dict[int | Literal[False], str | Literal[False] | None]:
        _res_ids = self._notify_reply_to_scope()[2]
        if defaults is None:
            defaults = dict.fromkeys(_res_ids, False)
        if author_ids is None:
            author_ids = dict.fromkeys(_res_ids, False)

        if set(defaults.keys()) != set(_res_ids):
            raise ValueError(
                f"Invalid defaults, keys {defaults.keys()} does not match recordset IDs {_res_ids}"
            )
        if set(author_ids.keys()) != set(_res_ids):
            raise ValueError(
                f"Invalid author_ids, keys {author_ids.keys()} does not match recordset IDs {_res_ids}"
            )

        reply_to_email = self._notify_get_reply_to_addresses()
        format_reply_to = self._notify_reply_to_formatter()

        reply_to_formatted = dict(defaults)
        for res_id, record_reply_to in reply_to_email.items():
            reply_to_formatted[res_id] = format_reply_to(
                record_reply_to, author_ids[res_id]
            )

        return reply_to_formatted

    def _notify_get_reply_to_per_author(
        self, author_pairs: Collection[tuple[int | Literal[False], str | None]]
    ) -> dict[tuple, dict]:
        keys = self._notify_reply_to_scope()[2]
        reply_to_email = self._notify_get_reply_to_addresses()
        format_reply_to = self._notify_reply_to_formatter()
        result = {}
        for author_id, author_email in author_pairs:
            formatted = dict.fromkeys(keys, author_email)
            for res_id, record_reply_to in reply_to_email.items():
                formatted[res_id] = format_reply_to(record_reply_to, author_id)
            result[(author_id, author_email)] = formatted
        return result

    def _notify_reply_to_formatter(
        self,
    ) -> Callable[[str, int | Literal[False]], str]:
        cache: dict[tuple[int | Literal[False], str], str] = {}

        def formatted(record_email: str, author_id: int | Literal[False]) -> str:
            key = (author_id, record_email)
            if key not in cache:
                cache[key] = self._notify_get_reply_to_formatted_email(
                    record_email, author_id=author_id
                )
            return cache[key]

        return formatted

    def _notify_get_reply_to_formatted_email(
        self, record_email: str, author_id: int | Literal[False] = False
    ) -> str:
        if len(record_email) >= _MAIL_REPLY_TO_LENGTH_LIMIT:
            _logger.warning(
                "Notification email address for reply-to is longer than %s characters. "
                "This might create non-compliant folding in the email header in certain DKIM "
                "verification tech stacks. It is advised to shorten it if possible. "
                "Reply-To: %s ",
                _MAIL_REPLY_TO_LENGTH_LIMIT,
                record_email,
            )
            return record_email

        if author_id:
            author_name = self.env["res.partner"].browse(author_id).name
        else:
            author_name = self.env.user.name

        formatted_email = tools.formataddr((author_name, record_email))
        if len(formatted_email) > _MAIL_REPLY_TO_LENGTH_LIMIT:
            formatted_email = tools.formataddr((self.env.user.name, record_email))
        if len(formatted_email) > _MAIL_REPLY_TO_LENGTH_LIMIT:
            formatted_email = record_email
        return formatted_email

    def _alias_resolve_error(
        self, message: EmailMessage, message_dict: dict[str, Any], alias: MailAlias
    ) -> AliasError | Literal[False]:
        author = self.env["res.partner"].browse(message_dict.get("author_id", False))
        if alias.alias_contact == "followers":
            if not self.ids:
                return AliasError(
                    "config_follower_no_record",
                    self.env._(
                        "incorrectly configured alias (unknown reference record)"
                    ),
                    is_config_error=True,
                )
            if "message_partner_ids" not in self._fields:
                return AliasError(
                    "config_follower_no_partners",
                    self.env._("incorrectly configured alias"),
                    is_config_error=True,
                )
            if not author or author not in self.message_partner_ids:
                return AliasError(
                    "error_follower_not_following",
                    self.env._("restricted to followers"),
                )
        elif alias.alias_contact == "partners" and not author:
            return AliasError(
                "error_partners_no_partner", self.env._("restricted to known authors")
            )
        return False

    @api.model
    def _get_default_activity_view(self) -> etree._Element:
        field = E.field(name=self._get_rec_name_fallback())
        activity_box = E.div(field, {"t-name": "activity-box"})
        templates = E.templates(activity_box)
        return E.activity(templates, string=self._description)

    def _mail_get_message_subtypes(self) -> MailMessageSubtype:
        return self.env["mail.message.subtype"].search(
            [
                "&",
                ("hidden", "=", False),
                "|",
                ("res_model", "=", self._name),
                ("res_model", "=", False),
            ]
        )

    def _notify_by_email_get_headers(
        self, headers: dict[str, str] | None = None
    ) -> dict[str, str]:
        headers = dict(headers or {})
        if not self:
            return headers
        self.check_singleton()
        headers.setdefault("X-Odoo-Objects", f"{self._name}-{self.id}")
        if "Return-Path" not in headers:
            company = self._mail_get_companies(default=self.env.company)[self.id]
            if company.bounce_email:
                headers["Return-Path"] = company.bounce_email
        return headers

    def _get_html_link(self, title: str | None = None) -> Markup:
        self.check_singleton()
        return Markup("<a href=# data-oe-model='%s' data-oe-id='%s'>%s</a>") % (
            self._name,
            self.id,
            title or self.display_name,
        )

    @api.model
    def _get_backend_root_menu_ids(self) -> list[int]:
        return []

    def _mail_get_field_path_value(self, field_path: str) -> str:
        if self:
            self.check_singleton()
        if not field_path:
            return ""

        last_model_path, _dot, last_fname = field_path.rpartition(".")
        try:
            last_model = self.mapped(last_model_path) if last_model_path else self
            last_field = last_model._fields[last_fname]
        except exceptions.UserError:
            raise
        except (KeyError, AttributeError) as err:
            raise exceptions.UserError(
                self.env._(
                    "%(model_name)s.%(field_path)s does not seem to be a valid field path",
                    model_name=self._name,
                    field_path=field_path,
                )
            ) from err
        except Exception as err:
            _logger.warning(
                "Could not read field path %s.%s", self._name, field_path, exc_info=True
            )
            raise exceptions.UserError(
                self.env._(
                    "We were not able to fetch value of field '%(field)s'",
                    field=field_path,
                )
            ) from err

        if last_field.relational:
            return " ".join(
                (value.display_name or "") for value in last_model.mapped(last_fname)
            )

        keep_falsy = last_field.type == "boolean"
        return " ".join(
            self._mail_format_field_value(value, last_field, record)
            for record, value in ((rec, rec[last_fname]) for rec in last_model)
            if keep_falsy or (value is not False and value is not None and value != "")
        )

    def _mail_format_field_value(
        self, value: Any, field: fields.Field, record: models.Model
    ) -> str:
        if field.type == "selection":
            return field.convert_to_export(value, record) or ""
        if field.type == "datetime":
            tz = (self and self._mail_get_timezone()) or self.env.user.tz or "UTC"
            return f"{tools.format_datetime(self.env, value, tz=tz)} {tz}"
        if field.type == "date":
            return tools.format_date(self.env, value)
        if field.type == "monetary":
            currency_fname = field.get_currency_field(record)
            currency = record[currency_fname] if record and currency_fname else None
            return tools.formatLang(self.env, value, currency_obj=currency or None)
        if field.type == "float":
            digits = field.get_digits(self.env)
            return tools.formatLang(self.env, value, digits=digits[1] if digits else 2)
        if field.type == "boolean":
            return self.env._("Yes") if value else self.env._("No")
        return str(value)

    def _mail_get_timezone(self) -> str | None:
        return self._mail_first_field_value(
            self._mail_default_timezone_fields, _MAIL_TIMEZONE_FIELD_TYPES
        )
