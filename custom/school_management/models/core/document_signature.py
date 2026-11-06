from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class DocumentSignature(models.Model):
    _name = "university.document.signature"
    _description = "Document Signature"
    _order = "id desc"

    name = fields.Char(
        string="Signature Reference",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: "New",
    )
    student_id = fields.Many2one(
        "university.student",
        string="Student",
        required=True,
        ondelete="restrict",
    )
    fee_id = fields.Many2one(
        "university.fee",
        string="Fee Invoice",
        required=True,
        ondelete="restrict",
    )
    signature = fields.Binary(string="Signature")
    signed_name = fields.Char(string="Signed Name")
    state = fields.Selection(
        [("pending", "Pending"), ("signed", "Signed")],
        string="Status",
        default="pending",
        required=True,
    )
    signed_on = fields.Datetime(string="Signed On", readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "university.document.signature"
                ) or "New"
        return super().create(vals_list)

    @api.constrains("student_id", "fee_id")
    def _check_student_fee_consistency(self):
        for signature in self:
            if signature.fee_id and signature.fee_id.student_id != signature.student_id:
                raise ValidationError(
                    _("The selected fee invoice must belong to the same student as the signature.")
                )

    def write(self, vals):
        if not vals:
            return super().write(vals)

        signed_records = self.filtered(lambda signature: signature.state == "signed")
        if signed_records and set(vals) - {"state", "signed_on"}:
            raise UserError(
                _("Signed document signatures cannot be edited. Only the status and signed date can change.")
            )

        return super().write(vals)

    def action_signed(self):
        self.write({"state": "signed", "signed_on": fields.Datetime.now()})
