import base64
import json
from datetime import datetime

from odoo import fields, models
from odoo.exceptions import UserError


class SuiteDashboardSnapshot(models.Model):
    _name = "suite.dashboard.snapshot"
    _description = "Suite Dashboard Snapshot"
    _order = "create_date desc, id desc"

    workspace_id = fields.Many2one(
        "suite.dashboard.workspace",
        ondelete="set null",
    )
    owner_id = fields.Many2one(
        "res.users",
        required=True,
        default=lambda self: self.env.user,
        readonly=True,
    )
    name = fields.Char(required=True, default=lambda self: self._default_name())
    filter_state = fields.Text(help="JSON-serialized filters used to generate the PDF.")
    payload_json = fields.Text(readonly=True)
    attachment_id = fields.Many2one("ir.attachment", ondelete="set null", readonly=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("done", "Done"),
            ("error", "Error"),
        ],
        default="draft",
        required=True,
    )
    recipient_ids = fields.Many2many("res.partner", string="Recipients")
    sent_on = fields.Datetime(readonly=True)
    schedule_id = fields.Many2one("suite.dashboard.schedule", ondelete="set null")
    error_msg = fields.Text(readonly=True)

    @staticmethod
    def _default_name():
        return f"Dashboard Snapshot {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    def _decode_filter_state(self):
        self.ensure_one()
        if not self.filter_state:
            return {}
        try:
            return json.loads(self.filter_state)
        except json.JSONDecodeError:
            return {}

    def action_generate_snapshot(self):
        self.ensure_one()
        if not self.workspace_id:
            raise UserError("Select a workspace before generating a snapshot.")

        try:
            payload = self.workspace_id.get_dashboard_payload(self._decode_filter_state())
            pdf_content, _report_type = self.env["ir.actions.report"]._render_qweb_pdf(
                "suite_dashboard_core.report_suite_dashboard_snapshot",
                [self.id],
                data={"payload": payload},
            )
            attachment = self.env["ir.attachment"].create(
                {
                    "name": f"{self.name}.pdf",
                    "type": "binary",
                    "datas": base64.b64encode(pdf_content),
                    "res_model": self._name,
                    "res_id": self.id,
                    "mimetype": "application/pdf",
                }
            )
            self.write(
                {
                    "attachment_id": attachment.id,
                    "payload_json": json.dumps(payload, ensure_ascii=False, indent=2),
                    "state": "done",
                    "error_msg": False,
                }
            )
        except Exception as exc:  # pragma: no cover - keeps the record auditable
            self.write(
                {
                    "state": "error",
                    "error_msg": str(exc),
                }
            )
            raise

        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_download_attachment(self):
        self.ensure_one()
        if not self.attachment_id:
            raise UserError("Generate the PDF snapshot first.")
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{self.attachment_id.id}?download=true",
            "target": "self",
        }
