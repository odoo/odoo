import typing
from typing import Literal, Self

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.api import ValuesType
from odoo.exceptions import AccessError
from odoo.libs.debug_log import DebugLog
from odoo.models import GC_UNLINK_LIMIT
from odoo.tools.translate import _

from odoo.addons.mail.tools.discuss import Store, StoreFieldsInput
from odoo.addons.mail.tools.failure_type import DELIVERY_FAILURE_TYPES

if typing.TYPE_CHECKING:
    from .mail_mail import MailMail
    from .mail_message import MailMessage
    from .res_partner import ResPartner

_debug = DebugLog(__name__)


class MailNotification(models.Model):
    _name = "mail.notification"
    _table = "mail_notification"
    _rec_name = "res_partner_id"
    _log_access = False
    _description = "Message Notifications"

    author_id: ResPartner = fields.Many2one(
        comodel_name="res.partner",
        ondelete="set null",
    )
    mail_message_id: MailMessage = fields.Many2one(
        comodel_name="mail.message",
        string="Message",
        index=True,
        required=True,
        ondelete="cascade",
    )
    mail_mail_id: MailMail = fields.Many2one(
        comodel_name="mail.mail",
        string="Mail",
        index=True,
        help="Optional mail_mail ID. Used mainly to optimize searches.",
    )
    res_partner_id: ResPartner = fields.Many2one(
        comodel_name="res.partner",
        string="Recipient",
        index=True,
        ondelete="cascade",
    )
    mail_email_address = fields.Char(help="Recipient email address")
    notification_type = fields.Selection(
        selection=[("inbox", "Inbox"), ("email", "Email")],
        default="inbox",
        index=True,
        required=True,
    )
    notification_status = fields.Selection(
        selection=[
            ("ready", "Ready to Send"),
            ("process", "Processing"),
            (
                "pending",
                "Sent",
            ),
            ("sent", "Delivered"),
            ("bounce", "Bounced"),
            ("exception", "Exception"),
            ("canceled", "Cancelled"),
        ],
        string="Status",
        default="ready",
        index=True,
    )
    is_read = fields.Boolean(index=True)
    read_date = fields.Datetime(copy=False)
    failure_type = fields.Selection(
        selection=DELIVERY_FAILURE_TYPES,
        string="Failure type",
    )
    failure_reason = fields.Text(
        string="Failure reason",
        copy=False,
    )

    _notification_partner_required = models.Constraint(
        "CHECK(notification_type != 'inbox' OR res_partner_id IS NOT NULL)",
        "Customer is required for inbox notification",
    )
    _notification_partner_or_email_required = models.Constraint(
        "CHECK(notification_type != 'email' OR failure_type IS NOT NULL OR res_partner_id IS NOT NULL OR COALESCE(mail_email_address, '') != '')",
        "Customer or email is required for inbox / email notification",
    )
    _res_partner_id_is_read_notification_status_mail_message_id = models.Index(
        "(res_partner_id, is_read, notification_status, mail_message_id)"
    )
    _author_id_notification_status_failure = models.Index(
        "(author_id, notification_status) WHERE notification_status IN ('bounce', 'exception')"
    )
    _unique_mail_message_id_res_partner_id_ = models.UniqueIndex(
        "(mail_message_id, res_partner_id) WHERE res_partner_id IS NOT NULL"
    )

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        messages = self.env["mail.message"].browse(
            vals["mail_message_id"] for vals in vals_list
        )
        messages.check_access("write")
        for vals in vals_list:
            if vals.get("is_read"):
                vals["read_date"] = fields.Datetime.now()
        notifications = super().create(vals_list)
        _debug.lifecycle(
            "create",
            count=len(notifications),
            messages=len(messages),
            types=sorted({vals.get("notification_type") or "" for vals in vals_list}),
            statuses=sorted(
                {vals.get("notification_status") or "" for vals in vals_list}
            ),
        )
        notifications.mail_message_id._invalidate_notification_state()
        return notifications

    def write(self, vals: ValuesType) -> Literal[True]:
        if (
            "mail_message_id" in vals or "res_partner_id" in vals
        ) and not self.env.is_admin():
            raise AccessError(
                _("Can not update the message or recipient of a notification.")
            )
        if vals.get("is_read"):
            vals["read_date"] = fields.Datetime.now()
        res = super().write(vals)
        _debug.lifecycle(
            "write",
            count=len(self),
            fields=list(vals),
            status=vals.get("notification_status"),
            failure_type=vals.get("failure_type"),
        )
        if vals.keys() & {
            "is_read",
            "notification_status",
            "res_partner_id",
            "mail_message_id",
        }:
            self.mail_message_id._invalidate_notification_state()
        return res

    @api.model
    def _gc_notifications(self, max_age_days: int = 180) -> tuple:
        domain = [
            ("is_read", "=", True),
            (
                "read_date",
                "<",
                fields.Datetime.now() - relativedelta(days=max_age_days),
            ),
            ("notification_status", "in", ("sent", "canceled")),
        ]
        records = self.search(domain, limit=GC_UNLINK_LIMIT)
        _debug.lifecycle(
            "gc_notifications", removed=len(records), max_age_days=max_age_days
        )
        records.unlink()
        return len(records), len(records) == GC_UNLINK_LIMIT

    def format_failure_reason(self) -> str:
        self.check_singleton()
        if self.failure_type != "unknown":
            return dict(
                self._fields["failure_type"]._description_selection(self.env)
            ).get(self.failure_type, _("No Error"))
        else:
            if self.failure_reason:
                return _("Unknown error: %(error)s", error=self.failure_reason)
            return _("Unknown error")

    def _filtered_for_web_client(self) -> Self:
        def _is_relevant_for_web_client(notif: MailNotification) -> bool:
            if (
                notif.notification_status in ["bounce", "exception", "canceled"]
                or notif.res_partner_id.partner_share
                or notif.mail_email_address
            ):
                return True
            subtype = notif.mail_message_id.subtype_id
            return not subtype or subtype.track_recipients

        return self.filtered(_is_relevant_for_web_client)

    def _to_store_defaults(self, target: Store.Target) -> StoreFieldsInput:
        return [
            "mail_email_address",
            "failure_type",
            "mail_message_id",
            "notification_status",
            "notification_type",
            Store.One(
                "res_partner_id",
                [
                    "name",
                    "email",
                    Store.Attr("display_name", predicate=lambda p: not p.name),
                ],
            ),
        ]
