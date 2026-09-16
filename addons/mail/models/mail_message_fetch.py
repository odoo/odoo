import contextlib
from typing import Any, Literal, Self

from odoo import api, models
from odoo.api import DomainType
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog

from odoo.addons.mail.tools.paging import (
    FETCH_LIMIT_DEFAULT,
    FETCH_LIMIT_MAX,
    FETCH_PARAMS,
    clamp_limit,
)

_debug = DebugLog(__name__)


class MailMessage(models.Model):
    _inherit = "mail.message"

    _SEARCH_COUNT_CAP = 1000

    @api.model
    def _clamp_fetch_limit(self, limit: int) -> int:
        return clamp_limit(
            limit,
            default=FETCH_LIMIT_DEFAULT,
            maximum=FETCH_LIMIT_MAX,
        )

    @api.model
    def _to_message_cursor(
        self, value: int | str | Literal[False] | None
    ) -> int | None:
        if value is None or value is False:
            return None
        try:
            return int(value)
        except TypeError, ValueError:
            return None

    @api.model
    def _to_search_term(self, value: Any) -> str | None:
        return value if isinstance(value, str) and value else None

    @api.model
    def _to_notification_filter(self, value: Any) -> bool | None:
        return value if isinstance(value, bool) else None

    @api.model
    def _filter_fetch_params(self, fetch_params: Any) -> dict:
        if not isinstance(fetch_params, dict):
            return {}
        return {
            key: value for key, value in fetch_params.items() if key in FETCH_PARAMS
        }

    def _message_fetch(
        self,
        domain: DomainType | None,
        *,
        thread: models.BaseModel | None = None,
        search_term: str | None = None,
        is_notification: bool | None = None,
        before: int | Literal[False] | None = None,
        after: int | Literal[False] | None = None,
        around: int | Literal[False] | None = None,
        limit: int = FETCH_LIMIT_DEFAULT,
    ) -> dict:
        limit = self._clamp_fetch_limit(limit)
        before = self._to_message_cursor(before)
        after = self._to_message_cursor(after)
        around = self._to_message_cursor(around)
        search_term = self._to_search_term(search_term)
        is_notification = self._to_notification_filter(is_notification)
        res = {}
        domain = Domain(True if domain is None else domain)
        domain &= self._get_domain_scope(thread=thread, is_notification=is_notification)
        if search_term:
            domain &= self._get_domain_text_search(
                search_term, thread=thread, is_notification=is_notification
            )
        if search_term or is_notification is not None:
            count = self.search_count(domain, limit=self._SEARCH_COUNT_CAP)
            res["count"] = count
            res["count_is_capped"] = count >= self._SEARCH_COUNT_CAP
        with _debug.perf(
            "message_fetch",
            cr=self.env.cr,
            model=thread._name if thread else None,
            record=thread.id if thread else None,
            search=bool(search_term),
            notification=is_notification,
            before=before,
            after=after,
            around=around,
            limit=limit,
        ) as span:
            if around is not None:
                res["messages"] = self._get_page_around(domain, around, limit)
            else:
                res["messages"] = self._get_page(
                    domain, before=before, after=after, limit=limit
                )
            span.set(messages=len(res["messages"]), count=res.get("count"))
        return res

    def _get_domain_scope(
        self,
        *,
        thread: models.BaseModel | None = None,
        is_notification: bool | None = None,
    ) -> Domain:
        domain = Domain.TRUE
        if thread:
            domain &= (
                Domain("res_id", "=", thread.id)
                & Domain("model", "=", thread._name)
                & Domain("message_type", "!=", "user_notification")
            )
        if is_notification is True:
            domain &= Domain("message_type", "=", "notification")
        elif is_notification is False:
            domain &= Domain("message_type", "!=", "notification")
        return domain

    def _get_domain_text_search(
        self,
        search_term: str,
        *,
        thread: models.BaseModel | None = None,
        is_notification: bool | None = None,
    ) -> Domain:
        search_term = (
            search_term.replace("\\", "\\\\")
            .replace("%", "\\%")
            .replace("_", "\\_")
            .replace(" ", "%")
        )
        attachment_domain = Domain("name", "ilike", search_term)
        if thread:
            attachment_domain &= Domain("res_model", "=", thread._name) & Domain(
                "res_id", "=", thread.id
            )
        domain = Domain.OR(
            [
                [
                    (
                        "attachment_ids",
                        "in",
                        self.env["ir.attachment"].sudo()._search(attachment_domain),
                    )
                ],
                [("body", "ilike", search_term)],
                [("subject", "ilike", search_term)],
                [("subtype_id.description", "ilike", search_term)],
            ]
        )
        _debug.logic(
            "text_search_domain",
            model=thread._name if thread else None,
            record=thread.id if thread else None,
            term_length=len(search_term),
            with_tracking=bool(thread and is_notification is not False),
        )
        if thread and is_notification is not False:
            domain |= Domain(
                "id", "in", self._search_tracking_message_ids(search_term, thread)
            )
        return domain

    def _search_tracking_message_ids(
        self, search_term: str, thread: models.BaseModel
    ) -> list[int]:
        tracking_value_domain = (
            Domain("mail_message_id.res_id", "=", thread.id)
            & Domain("mail_message_id.model", "=", thread._name)
            & self._get_domain_tracking_values(search_term)
        )
        tracking_values = (
            self.env["mail.tracking.value"].sudo().search(tracking_value_domain)
        )
        _debug.perf.count(
            "tracking_search",
            model=thread._name,
            record=thread.id,
            values=len(tracking_values),
        )
        return tracking_values._filtered_has_field_access(self.env).mail_message_id.ids

    def _get_page_around(self, domain: Domain, around: int, limit: int) -> Self:
        after_limit = limit // 2
        before_limit = limit - after_limit
        messages_before = self.search(
            domain & Domain("id", "<=", around), limit=before_limit, order="id DESC"
        )
        messages_after = (
            self.search(
                domain & Domain("id", ">", around), limit=after_limit, order="id ASC"
            )
            if after_limit
            else self.browse()
        )
        return (messages_after + messages_before).sorted("id", reverse=True)

    def _get_page(
        self,
        domain: Domain,
        *,
        before: int | None = None,
        after: int | None = None,
        limit: int = FETCH_LIMIT_DEFAULT,
    ) -> Self:
        if before:
            domain &= Domain("id", "<", before)
        if after:
            domain &= Domain("id", ">", after)
        messages = self.search(
            domain, limit=limit, order="id ASC" if after else "id DESC"
        )
        return messages.sorted("id", reverse=True) if after else messages

    def _get_domain_tracking_values(self, search_term: str) -> Domain:
        numeric_term = None
        with contextlib.suppress(ValueError, TypeError):
            numeric_term = float(search_term)
        domain = Domain.OR(
            Domain(field_name, "ilike", search_term)
            for field_name in (
                "old_value_char",
                "new_value_char",
                "old_value_text",
                "new_value_text",
                "old_value_datetime",
                "new_value_datetime",
                "field_id.name",
                "field_id.field_description",
            )
        )
        if numeric_term is not None:
            epsilon = 1e-9
            domain |= Domain("field_id.ttype", "in", ("float", "monetary")) & Domain.OR(
                Domain(field_name, ">=", numeric_term - epsilon)
                & Domain(field_name, "<=", numeric_term + epsilon)
                for field_name in ("old_value_float", "new_value_float")
            )
            if numeric_term.is_integer():
                domain |= Domain("field_id.ttype", "=", "integer") & Domain.OR(
                    Domain(field_name, "=", int(numeric_term))
                    for field_name in ("old_value_integer", "new_value_integer")
                )
        return domain
