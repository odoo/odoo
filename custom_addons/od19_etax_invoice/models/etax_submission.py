# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""Hand-over of e-Tax documents to the Revenue Department.

An ``od19.etax.submission`` is one submission event.  It groups the e-Tax
documents that were sent together, records the RD response — reference, code
and message — and keeps the retry history so the tax authority outcome of
every document is traceable.

Two channels are offered:

* Online, through the gateway adapter (:mod:`..lib.rd_gateway`).  The RD API
  contract is not published yet, so the mock adapter is the default and the
  whole flow — state, reference, response code, retries — works today.
* Offline fallback: when the online channel is unavailable the documents are
  exported as a signed ZIP batch (:mod:`..lib.batch_export`) whose
  ``manifest.txt`` is the audit trail of the batch.
"""

import base64
import re

from odoo import api, fields, models
from odoo.exceptions import UserError

from ..lib.batch_export import build_batch_zip
from ..lib.rd_gateway import RdGatewayError, get_gateway

#: Response code returned by the RD (and by the mock adapter) on acceptance.
ACCEPTED_CODE = "0"


class Od19EtaxSubmission(models.Model):
    _name = "od19.etax.submission"
    _description = "e-Tax Invoice RD Submission"
    _inherit = ["mail.thread"]
    _order = "submitted_at desc, id desc"

    name = fields.Char(
        string="Submission Reference",
        required=True,
        copy=False,
        readonly=True,
        default="New",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        ondelete="cascade",
    )
    document_ids = fields.Many2many(
        "od19.etax.document",
        "od19_etax_submission_document_rel",
        "submission_id",
        "document_id",
        string="e-Tax Documents",
        required=True,
    )
    channel = fields.Selection(
        [("mock", "Mock (ทดสอบ)"), ("live", "Live (RD)")],
        string="Channel",
        default="mock",
        required=True,
        readonly=True,
        copy=False,
        help="Channel used for the last attempt; captured when submitting.",
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("accepted", "Accepted"),
            ("rejected", "Rejected"),
            ("failed", "Failed"),
        ],
        default="draft",
        required=True,
        copy=False,
        tracking=True,
    )
    submitted_at = fields.Datetime(string="Submitted On", readonly=True, copy=False)
    attempt_count = fields.Integer(
        string="Attempts",
        default=0,
        readonly=True,
        copy=False,
        help="Number of times the documents were sent to the RD.",
    )
    reference = fields.Char(
        string="RD Reference",
        readonly=True,
        copy=False,
        help="Reference returned by the RD for the accepted document(s).",
    )
    response_code = fields.Char(readonly=True, copy=False)
    response_message = fields.Text(readonly=True, copy=False)

    batch_file = fields.Binary(
        string="Batch Archive",
        attachment=True,
        copy=False,
        help="ZIP archive of the signed XML and PDF of every document, with "
        "the manifest.txt audit trail.",
    )
    batch_filename = fields.Char(copy=False)
    batch_exported_at = fields.Datetime(readonly=True, copy=False)

    note = fields.Text()

    od19_etax_enabled = fields.Boolean(
        related="company_id.od19_etax_enabled",
        string="e-Tax Invoice Enabled",
        readonly=True,
    )

    # ------------------------------------------------------------------
    # Naming
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals["name"] == "New":
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("od19.etax.submission")
                    or "New"
                )
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Submission
    # ------------------------------------------------------------------
    def _batch_filename(self):
        self.ensure_one()
        stem = re.sub(r"[^A-Za-z0-9._-]+", "_", self.name or "batch")
        return "etax-batch-%s.zip" % stem

    def action_submit(self):
        """Send every document of the submission through the RD gateway."""
        self.ensure_one()
        self.company_id._od19_etax_check_enabled()
        if self.state == "accepted":
            raise UserError(
                self.env._(
                    "This submission has already been accepted by the RD and "
                    "cannot be submitted again."
                )
            )
        if not self.document_ids:
            raise UserError(
                self.env._("กรุณาเลือกเอกสาร e-Tax ที่ต้องการนำส่งก่อน")
            )
        gateway = get_gateway(self.company_id)
        references = []
        codes = []
        messages = []
        errors = 0
        for document in self.document_ids:
            try:
                response = gateway.submit(document)
            except RdGatewayError as error:
                errors += 1
                messages.append("%s: %s" % (document.name, error))
                continue
            code = response.get("response_code") or ""
            codes.append(code)
            references.append(response.get("ref") or "")
            messages.append(
                "%s: [%s] %s"
                % (document.name, code, response.get("response_message") or "")
            )
            if code != ACCEPTED_CODE:
                errors += 1

        if errors and not codes:
            state = "failed"
        elif errors:
            state = "rejected"
        else:
            state = "accepted"

        self.write({
            "channel": gateway.mode,
            "state": state,
            "submitted_at": fields.Datetime.now(),
            "attempt_count": self.attempt_count + 1,
            "reference": ", ".join(filter(None, references)),
            "response_code": codes[-1] if codes else "",
            "response_message": "\n".join(messages),
        })
        self.message_post(
            body=self.env._(
                "นำส่งเอกสาร %(count)s รายการผ่านช่องทาง %(channel)s — ผลลัพธ์: %(state)s",
                count=len(self.document_ids),
                channel=gateway.mode,
                state=dict(self._fields["state"].selection).get(state, state),
            )
        )
        return True

    def action_retry(self):
        """Re-send the documents of every failed or rejected submission."""
        for submission in self:
            if submission.state in ("failed", "rejected"):
                submission.action_submit()
        return True

    # ------------------------------------------------------------------
    # Offline fallback
    # ------------------------------------------------------------------
    def action_export_batch(self):
        """Build the signed ZIP batch used when the online channel is down."""
        self.ensure_one()
        self.company_id._od19_etax_check_enabled()
        if not self.document_ids:
            raise UserError(
                self.env._("กรุณาเลือกเอกสาร e-Tax ที่ต้องการส่งออกก่อน")
            )
        try:
            content = build_batch_zip(self.document_ids)
        except ValueError as error:
            raise UserError(
                self.env._("ไม่สามารถสร้างชุดไฟล์นำส่งได้: %s", error)
            ) from error
        self.write({
            "batch_file": base64.b64encode(content),
            "batch_filename": self._batch_filename(),
            "batch_exported_at": fields.Datetime.now(),
        })
        self.message_post(
            body=self.env._(
                "สร้างชุดไฟล์สำรอง (batch export) สำหรับนำส่งด้วยช่องทางสำรองแล้ว"
            )
        )
        return True
