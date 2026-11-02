# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""Hand-over of withholding records to the e-Withholding Tax service.

An ``od19.ewht.submission`` is one submission event. It groups the
``account.withholding.move`` records (one per vendor payment) that were sent to
the bank, records the bank response — reference, code and message — and keeps
the retry history so the filing outcome of every withholding record is
traceable.

The channel is resolved by the gateway adapter (:mod:`..lib.ewht_gateway`).
The bank API contract is not published in a stable form, so the mock adapter is
the default and the whole flow — state, reference, response code, retries —
works today.
"""

from odoo import api, fields, models
from odoo.exceptions import UserError

from ..lib.ewht_gateway import EwhtGatewayError, get_gateway

#: Response code returned by the bank (and by the mock adapter) on acceptance.
ACCEPTED_CODE = "0"


class Od19EwhtSubmission(models.Model):
    _name = "od19.ewht.submission"
    _description = "e-Withholding Tax Submission"
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
    move_ids = fields.Many2many(
        "account.withholding.move",
        "od19_ewht_submission_move_rel",
        "submission_id",
        "wht_move_id",
        string="Withholding Records",
        required=True,
    )
    channel = fields.Selection(
        [("mock", "Mock (ทดสอบ)"), ("live", "Live (ธนาคาร)")],
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
        help="Number of times the records were sent to the bank.",
    )
    reference = fields.Char(
        string="Bank Reference",
        readonly=True,
        copy=False,
        help="Reference returned by the bank for the accepted record(s).",
    )
    response_code = fields.Char(readonly=True, copy=False)
    response_message = fields.Text(readonly=True, copy=False)

    note = fields.Text()

    od19_ewht_enabled = fields.Boolean(
        related="company_id.od19_ewht_enabled",
        string="e-Withholding Tax Enabled",
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
                    self.env["ir.sequence"].next_by_code("od19.ewht.submission")
                    or "New"
                )
        records = super().create(vals_list)
        # Nothing may be filed for a company that never opted in to e-WHT.
        for record in records:
            record.company_id._od19_ewht_check_enabled()
        return records

    # ------------------------------------------------------------------
    # Submission
    # ------------------------------------------------------------------
    def action_submit(self):
        """Send every withholding record of the submission through the bank."""
        self.ensure_one()
        self.company_id._od19_ewht_check_enabled()
        if self.state == "accepted":
            raise UserError(
                self.env._(
                    "รายการนำส่งนี้ธนาคารตอบรับแล้ว ไม่สามารถนำส่งซ้ำได้"
                )
            )
        if not self.move_ids:
            raise UserError(
                self.env._("กรุณาเลือกรายการหัก ณ ที่จ่ายที่ต้องการนำส่งก่อน")
            )
        gateway = get_gateway(self.company_id)
        references = []
        codes = []
        messages = []
        errors = 0
        for wht_move in self.move_ids:
            try:
                response = gateway.submit(wht_move)
            except EwhtGatewayError as error:
                errors += 1
                messages.append("%s: %s" % (wht_move.id, error))
                continue
            code = response.get("response_code") or ""
            codes.append(code)
            references.append(response.get("ref") or "")
            messages.append(
                "%s: [%s] %s"
                % (wht_move.id, code, response.get("response_message") or "")
            )
            if code != ACCEPTED_CODE:
                errors += 1

        if errors and not codes:
            state = "failed"
        elif errors:
            state = "rejected"
        else:
            state = "accepted"

        self.write(
            {
                "channel": gateway.mode,
                "state": state,
                "submitted_at": fields.Datetime.now(),
                "attempt_count": self.attempt_count + 1,
                "reference": ", ".join(filter(None, references)),
                "response_code": codes[-1] if codes else "",
                "response_message": "\n".join(messages),
            }
        )
        self.message_post(
            body=self.env._(
                "นำส่งรายการหัก ณ ที่จ่าย %(count)s รายการผ่านช่องทาง "
                "%(channel)s — ผลลัพธ์: %(state)s",
                count=len(self.move_ids),
                channel=gateway.mode,
                state=dict(self._fields["state"].selection).get(state, state),
            )
        )
        return True

    def action_retry(self):
        """Re-send the records of every failed or rejected submission."""
        for submission in self:
            if submission.state in ("failed", "rejected"):
                submission.action_submit()
        return True
