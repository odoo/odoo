import logging
from typing import Any

from odoo import api, fields, models, tools
from odoo.api import DomainType
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.http import request

_logger = logging.getLogger(__name__)

SKIP_CAPTCHA_LOGIN = object()


class ResUsers(models.Model):
    _inherit = "res.users"

    color_scheme = fields.Selection(
        related="res_users_settings_id.color_scheme",
        readonly=False,
    )

    @property
    def SELF_READABLE_FIELDS(self) -> list[str]:
        return super().SELF_READABLE_FIELDS + ["color_scheme"]

    @property
    def SELF_WRITEABLE_FIELDS(self) -> list[str]:
        return super().SELF_WRITEABLE_FIELDS + ["color_scheme"]

    @api.model
    def name_search(
        self,
        name: str = "",
        domain: DomainType | None = None,
        operator: str = "ilike",
        limit: int = 100,
    ) -> list[tuple[int, str]]:
        domain = Domain(domain or Domain.TRUE)
        user_list = super().name_search(name, domain, operator, limit)
        uid = self.env.uid
        if (
            index := next(
                (i for i, (user_id, _name) in enumerate(user_list) if user_id == uid),
                None,
            )
        ) is not None:
            user_tuple = user_list.pop(index)
            user_list.insert(0, user_tuple)
        elif limit is not None and len(user_list) == limit:
            if user_tuple := super().name_search(
                name, domain & Domain("id", "=", uid), operator, limit=1
            ):
                user_list = [user_tuple[0], *user_list[:-1]]
        return user_list

    def _on_webclient_bootstrap(self) -> None:
        self.check_singleton()

    def _is_captcha_login_required(self, credential: dict[str, Any]) -> bool:
        if (
            request
            and request.env.context.get("skip_captcha_login") is SKIP_CAPTCHA_LOGIN
        ):
            return False
        return credential["type"] == "password"

    @api.model
    def web_create_users(self, emails: list[str]) -> bool:
        emails_normalized = [
            tools.mail.parse_contact_from_email(email)[1] for email in emails
        ]

        if "email_normalized" not in self._fields:
            raise UserError(
                self.env._(
                    "You have to install the Discuss application to use this feature."
                )
            )

        invalid = [
            email
            for email, normalized in zip(emails, emails_normalized, strict=True)
            if not normalized
        ]
        if invalid:
            raise UserError(
                self.env._(
                    "The following email address(es) could not be parsed: %s",
                    ", ".join(map(repr, invalid)),
                )
            )

        all_matching = self.with_context(active_test=False).search(
            [
                "|",
                ("login", "in", emails + emails_normalized),
                ("email_normalized", "in", emails_normalized),
            ]
        )
        deactivated_users = all_matching.filtered(lambda u: not u.active)
        for user in deactivated_users:
            _logger.info(
                "Reactivating previously deactivated user %r (id=%d)",
                user.login,
                user.id,
            )
        if deactivated_users:
            deactivated_users.active = True
        done = set(all_matching.mapped("email_normalized")) | set(
            all_matching.mapped("login")
        )

        seen = set(done)
        new_emails = []
        for e, n in zip(emails, emails_normalized, strict=True):
            if n not in seen:
                new_emails.append(e)
                seen.add(n)
        vals_list = []
        for email in new_emails:
            name, email_normalized = tools.mail.parse_contact_from_email(email)
            vals_list.append(
                {
                    "login": email_normalized,
                    "name": name or email_normalized,
                    "email": email_normalized,
                    "active": True,
                }
            )
        if vals_list:
            self.with_context(signup_valid=True).create(vals_list)

        return True
