import logging
from collections import defaultdict
from datetime import timedelta
from typing import Any

from markupsafe import Markup, escape

from odoo import api, fields, models
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


class DocumentDocument(models.Model):
    _inherit = "document.document"

    is_mandatory = fields.Boolean(
        related="document_type_id.is_mandatory",
        help="Whether this document type is required for compliance (inherited from document type)",
    )
    document_type_requires_original = fields.Boolean(
        related="document_type_id.requires_original",
        string="Type Requires Original",
    )
    notification_last_days = fields.Integer(
        default=0,
        copy=False,
        help="Smallest notification threshold, in days before expiration, already "
        "notified for this document (0 when none has been sent yet). Any threshold "
        "configured on the document type works, not only 30, 7 and 1",
    )
    notification_sent_expired = fields.Boolean(
        default=False,
        copy=False,
        help="Tracks if notification was sent when document reached expiration date",
    )

    compliance_state = fields.Selection(
        selection=[
            ("compliant", "Compliant"),
            ("non_compliant", "Non-Compliant"),
            ("na", "Not Applicable"),
        ],
        compute="_compute_compliance_state",
        store=True,
        help="Whether the document satisfies its type: Compliant (the type does not "
        "expire, or the document is not expired), Non-Compliant (expired, or "
        "missing its expiration date), Not Applicable (no document type)",
    )

    date_verification = fields.Date(
        copy=False,
        help="Date when this document was last reviewed and verified for accuracy",
    )
    verified_by_user_id = fields.Many2one(
        comodel_name="res.users",
        copy=False,
        help="User who last verified this document",
    )
    verification_notes = fields.Text(
        copy=False,
        help="Notes and observations from document verification process",
    )

    @api.depends("document_type_id.has_expiration", "expiration_state")
    def _compute_compliance_state(self) -> None:
        for doc in self:
            if not doc.document_type_id:
                doc.compliance_state = "na"
            elif doc.expiration_state in ("expired", "missing"):
                doc.compliance_state = "non_compliant"
            else:
                doc.compliance_state = "compliant"

    def action_record_verification(self) -> dict[str, Any]:
        self.check_singleton()
        _debug.lifecycle("document_verified", document=self, user=self.env.user)
        self.write(
            {
                "date_verification": fields.Date.context_today(self),
                "verified_by_user_id": self.env.user.id,
            }
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": self.env._("Document Verified"),
                "message": self.env._(
                    "Document %(name)s has been verified.",
                    name=self.name,
                ),
                "type": "success",
                "sticky": False,
            },
        }

    @api.model
    def cron_document_notifications(self) -> None:
        widest = self.env["document.type"]._get_widest_notification_days()
        _debug.pipeline("notification_cron_start", widest_days=widest)
        windows = list(self._iter_expiration_windows())
        has_expiration = Domain("document_type_id.has_expiration", "=", True)
        if widest:
            expiring = self.search(
                has_expiration
                & Domain.OR(
                    Domain(company_domain)
                    & Domain("date_expiration", ">=", today)
                    & Domain("date_expiration", "<=", today + timedelta(days=widest))
                    for today, company_domain in windows
                )
            )
            # Collected and written per threshold rather than per record:
            # the cron has no limit, so a per-record write is one UPDATE per
            # due document for the whole tenant in one transaction.
            notified_by_threshold = defaultdict(self.browse)
            for today, docs in expiring._group_by_expiration_today():
                for doc in docs:
                    days_left = (doc.date_expiration - today).days
                    threshold = doc._get_due_notification_threshold(days_left)
                    if threshold is None:
                        continue
                    if doc._send_expiration_notification(days_left):
                        notified_by_threshold[threshold] |= doc

            _debug.pipeline(
                "expiring_notified",
                candidates=expiring,
                thresholds=len(notified_by_threshold),
            )
            for threshold, notified in notified_by_threshold.items():
                notified.notification_last_days = threshold

        expired = self.search(
            has_expiration
            & Domain("notification_sent_expired", "=", False)
            & Domain.OR(
                Domain(company_domain) & Domain("date_expiration", "<", today)
                for today, company_domain in windows
            )
        )
        notified_expired = self.browse()
        for doc in expired:
            if doc._send_expiration_notification(None):
                notified_expired |= doc

        _debug.pipeline(
            "expired_notified", candidates=expired, notified=notified_expired
        )
        if notified_expired:
            notified_expired.notification_sent_expired = True

    def _get_due_notification_threshold(self, days_left: int) -> int | None:
        self.check_singleton()

        reached = [
            days
            for days in self.document_type_id._get_notification_days()
            if days >= days_left
        ]
        if not reached:
            _debug.logic("threshold_none", reason="no_threshold_reached", document=self)
            return None

        threshold = min(reached)
        if self.notification_last_days and threshold >= self.notification_last_days:
            _debug.logic("threshold_none", reason="already_notified", document=self)
            return None
        _debug.logic("threshold_due", document=self, threshold=threshold)
        return threshold

    def _recompute_expiration_state(self) -> None:
        super()._recompute_expiration_state()
        self.env.add_to_compute(self._fields["compliance_state"], self)
        self.flush_recordset(["compliance_state"])

    def _get_notification_recipients(self):
        self.check_singleton()
        partners = self.document_type_id.notification_partner_ids
        if self.owner_id:
            partners |= self.owner_id.partner_id
        return partners

    def _get_expiration_summary(self, days_left: int | None) -> str:
        if days_left is None:
            return self.env._("Document expired")
        if days_left == 0:
            return self.env._("Document expires today")
        return self.env._("Document expiring in %(days)s days", days=days_left)

    def _send_expiration_notification(self, days_left: int | None) -> bool:
        self.check_singleton()

        partners = self._get_notification_recipients()
        if not partners:
            _debug.logic("notification_skipped", reason="no_recipient", document=self)
            _logger.warning(
                "No notification recipients for document %s (ID: %s). "
                "Configure notification_partner_ids on type '%s' or set a document owner.",
                self.name,
                self.id,
                self.document_type_id.name,
            )
            return False

        summary = self._get_expiration_summary(days_left)
        activity_type = self.env.ref("mail.mail_activity_data_todo")
        note = self._get_expiration_note(days_left)

        notified = False
        users_with_activity = set(
            self.env["mail.activity"]
            .search(
                [
                    ("res_model", "=", self._name),
                    ("res_id", "=", self.id),
                    ("activity_type_id", "=", activity_type.id),
                    ("user_id", "in", partners.user_ids.ids),
                    ("summary", "=", summary),
                ]
            )
            .user_id.ids
        )
        for partner in partners:
            user = partner.user_ids[:1]
            if not user:
                _debug.logic(
                    "notification_recipient_skipped",
                    reason="no_user",
                    partner=partner,
                )
                _logger.info(
                    "Skipping notification recipient %s (ID: %s) for document %s "
                    "(ID: %s): the contact has no user to assign an activity to.",
                    partner.name,
                    partner.id,
                    self.name,
                    self.id,
                )
                continue

            notified = True

            if user.id in users_with_activity:
                _debug.logic("notification_deduplicated", document=self, user=user)
                continue

            _debug.lifecycle(
                "expiration_activity_scheduled",
                document=self,
                user=user,
                days_left=days_left if days_left is not None else -1,
            )
            self.activity_schedule(
                "mail.mail_activity_data_todo",
                date_deadline=self.date_expiration,
                user_id=user.id,
                summary=summary,
                note=note,
            )

        return notified

    def _get_expiration_note(self, days_left: int | None) -> str:
        self.check_singleton()

        if days_left is None:
            header = Markup(
                "<p>The following document has <strong>expired</strong>:</p>"
            )
        elif days_left == 0:
            header = Markup(
                "<p>The following document expires <strong>today</strong>:</p>"
            )
        else:
            header = (
                Markup(
                    "<p>The following document will expire in <strong>%s days</strong>:</p>"
                )
                % days_left
            )

        message = header + Markup(
            "<ul>"
            "<li><strong>Document:</strong> %s</li>"
            "<li><strong>Type:</strong> %s</li>"
            "<li><strong>Expiration Date:</strong> %s</li>"
            "</ul>"
        ) % (
            escape(self.name),
            escape(self.document_type_id.name),
            escape(str(self.date_expiration)),
        )

        if self.is_renewable and self.document_type_id.instructions:
            message += Markup(
                "<p><strong>Renewal Instructions:</strong></p>%s"
            ) % Markup(self.document_type_id.instructions)

        return str(message)
