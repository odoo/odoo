import typing
from types import NotImplementedType
from typing import Any

from odoo import _, api, fields, models, tools
from odoo.exceptions import AccessError, UserError
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL

if typing.TYPE_CHECKING:
    from .res_partner import ResPartner

_debug = DebugLog(__name__)


class MixinMailThreadBlacklist(models.AbstractModel):
    _name = "mixin.mail.thread.blacklist"
    _inherit = ["mixin.mail.thread"]
    _description = "Mail Blacklist mixin"
    _primary_email = "email"

    email_normalized = fields.Char(
        string="Normalized Email",
        compute="_compute_email_normalized",
        compute_sudo=True,
        store=True,
        index="btree_not_null",
        help="This field is used to search on email address as the primary email field can contain more than strictly an email address.",
    )
    is_blacklisted = fields.Boolean(
        string="Blacklist",
        compute="_compute_is_blacklisted",
        search="_search_is_blacklisted",
        compute_sudo=True,
        store=False,
        groups="base.group_user",
        help="If the email address is on the blacklist, the contact won't receive mass mailing anymore, from any list",
    )
    message_bounce = fields.Integer(
        string="Bounce",
        default=0,
        help="Counter of the number of bounced emails for this contact",
    )

    @api.depends(lambda self: [self._primary_email])
    def _compute_email_normalized(self) -> None:
        self._assert_primary_email()
        for record in self:
            record.email_normalized = tools.email_normalize(
                record[self._primary_email], strict=False
            )

    @api.model
    def _search_is_blacklisted(
        self, operator: str, value: Any
    ) -> list | NotImplementedType:
        if operator not in ("in", "not in"):
            return NotImplemented
        self.flush_model(["email_normalized"])
        self.env["mail.blacklist"].flush_model(["email", "active"])
        self._assert_primary_email()

        if operator == "in":
            sql = SQL(
                """
                SELECT m.id
                    FROM mail_blacklist bl
                    JOIN %s m
                    ON m.email_normalized = bl.email AND bl.active
            """,
                SQL.identifier(self._table),
            )
        else:
            sql = SQL(
                """
                SELECT m.id
                    FROM %s m
                    LEFT JOIN mail_blacklist bl
                    ON m.email_normalized = bl.email AND bl.active
                    WHERE bl.id IS NULL
            """,
                SQL.identifier(self._table),
            )

        return [("id", "in", SQL("(%s)", sql))]

    @api.depends("email_normalized")
    def _compute_is_blacklisted(self) -> None:
        blacklist = set(
            self.env["mail.blacklist"]
            .sudo()
            .with_context(active_test=True)
            .search([("email", "in", self.mapped("email_normalized"))])
            .mapped("email")
        )
        for record in self:
            record.is_blacklisted = record.email_normalized in blacklist

    def _assert_primary_email(self) -> None:
        if not hasattr(self, "_primary_email") or not isinstance(
            self._primary_email, str
        ):
            raise UserError(_("Invalid primary email field on model %s", self._name))
        if (
            self._primary_email not in self._fields
            or self._fields[self._primary_email].type != "char"
        ):
            raise UserError(_("Invalid primary email field on model %s", self._name))

    def _message_receive_bounce(self, email: str, partner: ResPartner) -> None:
        super()._message_receive_bounce(email, partner)
        _debug.lifecycle(
            "bounce_counted", model=self._name, records=self.ids, email=email
        )
        for bounce, records in self.grouped("message_bounce").items():
            records.write({"message_bounce": bounce + 1})

    def _message_reset_bounce(self, email: str) -> None:
        super()._message_reset_bounce(email)
        _debug.lifecycle(
            "bounce_reset", model=self._name, records=self.ids, email=email
        )
        self.write({"message_bounce": 0})

    def mail_action_blacklist_remove(self) -> dict:
        can_access = self.env["mail.blacklist"].has_access("write")
        if can_access:
            return {
                "name": _("Are you sure you want to unblacklist this Email Address?"),
                "type": "ir.actions.act_window",
                "view_mode": "form",
                "res_model": "mail.blacklist.remove",
                "target": "new",
            }
        else:
            raise AccessError(
                _(
                    "You do not have the access right to unblacklist emails. Please contact your administrator."
                )
            )

    @api.model
    def _get_domain_loop_sender(self, email_from_normalized: str) -> list:
        return [("email_normalized", "=", email_from_normalized)]
