import logging
from typing import Any

from odoo import api, models, tools
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.http import request
from odoo.orm._typing import DomainType

_logger = logging.getLogger(__name__)

SKIP_CAPTCHA_LOGIN = object()


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model
    def name_search(
        self,
        name: str = "",
        domain: DomainType | None = None,
        operator: str = "ilike",
        limit: int = 100,
    ) -> list[tuple[int, str]]:
        # if we have a search with a limit, move current user as the first result
        domain = Domain(domain or Domain.TRUE)
        user_list = super().name_search(name, domain, operator, limit)
        uid = self.env.uid
        # index 0 is correct not Falsy in this case, use None to avoid ignoring it
        if (
            index := next(
                (i for i, (user_id, _name) in enumerate(user_list) if user_id == uid),
                None,
            )
        ) is not None:
            # move found user first
            user_tuple = user_list.pop(index)
            user_list.insert(0, user_tuple)
        elif limit is not None and len(user_list) == limit:
            # user not found and limit reached, try to find the user again
            if user_tuple := super().name_search(
                name, domain & Domain("id", "=", uid), operator, limit=1
            ):
                user_list = [user_tuple[0], *user_list[:-1]]
        return user_list

    def _on_webclient_bootstrap(self) -> None:
        self.ensure_one()

    def _should_captcha_login(self, credential: dict[str, Any]) -> bool:
        if (
            request
            and request.env.context.get("skip_captcha_login") is SKIP_CAPTCHA_LOGIN
        ):
            return False
        return credential["type"] == "password"

    @api.model
    def web_create_users(self, emails: list[str]) -> bool:
        """Batch-create users from a list of email addresses.

        Reactivates deactivated accounts when the email matches an existing
        user. Requires the Discuss application for the ``email_normalized``
        field.
        """
        emails_normalized = [
            tools.mail.parse_contact_from_email(email)[1] for email in emails
        ]

        if "email_normalized" not in self._fields:
            raise UserError(
                self.env._(
                    "You have to install the Discuss application to use this feature."
                )
            )

        deactivated_users = self.with_context(active_test=False).search(
            [
                ("active", "=", False),
                "|",
                ("login", "in", emails + emails_normalized),
                ("email_normalized", "in", emails_normalized),
            ]
        )
        for user in deactivated_users:
            _logger.info(
                "Reactivating previously deactivated user %r (id=%d)",
                user.login,
                user.id,
            )
            user.active = True
        done = deactivated_users.mapped("email_normalized")

        new_emails = set(emails) - set(deactivated_users.mapped("email"))
        for email in new_emails:
            name, email_normalized = tools.mail.parse_contact_from_email(email)
            if email_normalized in done:
                continue
            self.with_context(signup_valid=True).create(
                {
                    "login": email_normalized,
                    "name": name or email_normalized,
                    "email": email_normalized,
                    "active": True,
                }
            )

        return True
