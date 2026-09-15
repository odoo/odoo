from typing import Any

from odoo import api, fields, models
from odoo.exceptions import ValidationError

# One badly configured type widens the notification cron's selection window for
# the whole tenant, so the configurable value carries a ceiling. Two years is
# well above anything the module ships or its demo data uses (180 is the widest).
MAX_NOTIFICATION_DAYS = 730


class DocumentType(models.Model):
    _inherit = "document.type"

    is_mandatory = fields.Boolean(
        default=False,
        help="Check if this document type is required for legal/regulatory compliance",
    )
    requires_original = fields.Boolean(
        default=False,
        help="Check if the physical original document must be kept on file (not just digital copy)",
    )

    applies_to = fields.Selection(
        selection="_selection_applies_to",
        default="all",
        help="Which kind of record this document type is required of. A vehicle "
        "registration applies to vehicles, not to suppliers: the compliance report "
        "only holds an entity to the mandatory types that apply to it",
    )

    notification_days = fields.Char(
        default="30,7,1",
        help="Comma-separated list of days before expiration to send "
        "notifications (e.g., '30,7,1' sends alerts 30, 7, and 1 days before "
        "expiration). The widest value configured on any type is how far ahead "
        f"the notification cron looks, so each one must be between 1 and "
        f"{MAX_NOTIFICATION_DAYS} days",
    )
    notification_partner_ids = fields.Many2many(
        comodel_name="res.partner",
        relation="document_type_partner_rel",
        column1="type_id",
        column2="partner_id",
        help="Additional contacts to notify about expiration (in addition to document owner)",
    )

    instructions = fields.Html(
        translate=True,
        help="HTML formatted instructions for obtaining, completing, or renewing documents of this type",
    )

    @api.model
    def _selection_applies_to(self) -> list[tuple[str, str]]:
        return [("all", "All Entities")] + [
            (model, self.env[model]._description)
            for model in self.env["document.compliance.report"]._get_entity_model_map()
        ]

    @api.model
    def _parse_notification_days(self, value: str | bool) -> list[int]:
        if not value:
            return []
        days = [int(part) for part in value.split(",") if part.strip()]
        if any(day <= 0 for day in days):
            raise ValueError("notification days must be positive")
        if any(day > MAX_NOTIFICATION_DAYS for day in days):
            raise ValueError(
                f"notification days must not exceed {MAX_NOTIFICATION_DAYS}"
            )
        if len(days) != len(set(days)):
            raise ValueError("notification days must not repeat")
        return days

    @api.constrains("notification_days")
    def _check_notification_days_format(self) -> None:
        for record in self:
            try:
                self._parse_notification_days(record.notification_days)
            except ValueError as err:
                raise ValidationError(
                    self.env._(
                        "Invalid notification days '%(value)s'. Use comma-separated, "
                        "distinct integers between 1 and %(maximum)s (e.g., 30,7,1). "
                        "The widest value configured on any document type is how far "
                        "ahead the notification cron selects documents, so an "
                        "unbounded one scans the whole table.",
                        value=record.notification_days,
                        maximum=MAX_NOTIFICATION_DAYS,
                    )
                ) from err

    def _get_notification_days(self) -> list[int]:
        self.check_singleton()
        return self._parse_notification_days(self.notification_days)

    def action_view_documents(self) -> dict[str, Any]:
        # Named explicitly: every form on document.document in core is a
        # special-purpose dialog, so core's "list,form" alone opens the
        # lowest-priority one -- the upload-url dialog.
        action = super().action_view_documents()
        action["views"] = [
            (self.env.ref("document.documents_view_list").id, "list"),
            (
                self.env.ref("document_compliance.documents_view_form_compliance").id,
                "form",
            ),
        ]
        compliance_filter = self.env.context.get("compliance_filter")
        if compliance_filter:
            action["domain"] = [
                *action["domain"],
                ("compliance_state", "=", compliance_filter),
            ]
        return action

    @api.model
    def _get_widest_notification_days(self) -> int:
        types = self.search([("has_expiration", "=", True)])
        return max(
            (
                max(days)
                for days in (doc_type._get_notification_days() for doc_type in types)
                if days
            ),
            default=0,
        )
