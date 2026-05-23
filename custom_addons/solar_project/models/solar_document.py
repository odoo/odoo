import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class SolarDocument(models.Model):
    _name = "solar.document"
    _description = "Solar Project Document"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "document_type_id, name"

    name = fields.Char(required=True, tracking=True)
    project_id = fields.Many2one(
        comodel_name="project.project",
        string="Project",
        required=True,
        ondelete="cascade",
        index=True,
    )
    task_id = fields.Many2one(
        comodel_name="project.task",
        string="Task",
        domain="[('project_id', '=', project_id)]",
        ondelete="set null",
    )
    document_type_id = fields.Many2one(
        comodel_name="solar.document.type",
        string="Document Type",
        required=True,
        ondelete="restrict",
        tracking=True,
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("review", "In Review"),
            ("approved", "Approved"),
            ("expired", "Expired"),
            ("superseded", "Superseded"),
        ],
        default="draft",
        required=True,
        tracking=True,
        string="Status",
    )
    attachment_id = fields.Many2one(
        comodel_name="ir.attachment",
        string="File",
        ondelete="set null",
    )
    valid_from = fields.Date(string="Valid From")
    valid_to = fields.Date(string="Valid Until")
    replaces_id = fields.Many2one(
        comodel_name="solar.document",
        string="Supersedes",
        help="Previous version of this document.",
        ondelete="set null",
    )
    notes = fields.Text(string="Notes")

    ai_extracted_data = fields.Json(
        string="AI Extracted Data",
        help="Structured data extracted by AI from the document.",
    )
    ai_classified = fields.Boolean(
        string="AI Classified",
        default=False,
    )

    def action_submit_review(self):
        self.write({"state": "review"})

    def action_approve(self):
        for rec in self:
            rec.state = "approved"
            if rec.replaces_id and rec.replaces_id.state not in (
                "superseded",
                "expired",
            ):
                rec.replaces_id.state = "superseded"

    def action_reset_draft(self):
        self.write({"state": "draft"})

    def action_expire(self):
        self.write({"state": "expired"})

    def _run_ai_classify(self):
        """Classify this document using solar.ai.service if available."""
        if "solar.ai.service" not in self.env:
            return

        for rec in self:
            attachment = rec.attachment_id
            if not attachment:
                continue
            text = attachment.name or ""
            if attachment.mimetype == "text/plain" and attachment.raw:
                text += "\n" + attachment.raw.decode("utf-8", errors="ignore")[:4000]

            service = self.env["solar.ai.service"]
            classification = service.classify_document_text(text)
            code = classification.get("document_type_code", "unknown")
            if code and code != "unknown":
                doc_type = self.env["solar.document.type"].search(
                    [("code", "=", code)],
                    limit=1,
                )
                if doc_type:
                    rec.document_type_id = doc_type
            rec.ai_classified = True
            rec.ai_extracted_data = classification
