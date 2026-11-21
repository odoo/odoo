# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class UniversityServiceRequest(models.Model):
    _name = "university.service.request"
    _description = "Unified Student Service Request"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "request_date desc, id desc"

    name = fields.Char(
        string="Request Number",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("New"),
    )
    student_id = fields.Many2one(
        "university.student",
        string="Student",
        required=True,
        default=lambda self: self._default_student_id(),
        tracking=True,
    )
    student_code = fields.Char(related="student_id.student_id", string="Student ID", readonly=True)
    program_id = fields.Many2one(related="student_id.program_id", string="Program", readonly=True)
    request_type = fields.Selection(
        [
            ("enrollment_cert", "Enrollment Certificate"),
            ("recommendation_letter", "Recommendation Letter"),
            ("leave_of_absence", "Leave of Absence / Deferment"),
            ("id_card_replacement", "Student ID Card Replacement"),
            ("complaint", "Feedback & Complaint"),
            ("transcript", "Official Transcript Request"),
        ],
        string="Request Type",
        required=True,
        default="enrollment_cert",
        tracking=True,
    )
    title = fields.Char(string="Subject / Title", required=True)
    description = fields.Text(string="Details / Purpose", required=True)
    request_date = fields.Date(
        string="Request Date",
        default=fields.Date.context_today,
        readonly=True,
    )
    semester_id = fields.Many2one(
        "university.semester",
        string="Target Semester (For Deferment/Absence)",
    )
    copies = fields.Integer(string="Number of Copies", default=1)
    delivery_method = fields.Selection(
        [
            ("digital", "Digital PDF via Portal"),
            ("campus_pickup", "Campus Pickup (Registrar Office)"),
            ("courier", "Postal Courier"),
        ],
        string="Delivery Method",
        default="digital",
    )
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "service_request_ir_attachments_rel",
        "request_id",
        "attachment_id",
        string="Supporting Documents",
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("pending", "Pending"),
            ("in_review", "In Review"),
            ("approved", "Approved"),
            ("completed", "Ready / Completed"),
            ("rejected", "Rejected"),
        ],
        string="Status",
        default="draft",
        tracking=True,
    )
    staff_notes = fields.Text(string="Staff Response / Notes", tracking=True)
    reviewed_by_id = fields.Many2one("res.users", string="Handled By", readonly=True)
    completed_at = fields.Datetime(string="Completed At", readonly=True)

    @api.model
    def _default_student_id(self):
        user = self.env.user
        student = self.env["university.student"].search([("user_id", "=", user.id)], limit=1)
        if not student and self.env.context.get("default_student_id"):
            student = self.env["university.student"].browse(self.env.context.get("default_student_id"))
        return student.id if student else False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                prefix = {
                    "enrollment_cert": "CERT",
                    "recommendation_letter": "REC",
                    "leave_of_absence": "LOA",
                    "id_card_replacement": "IDC",
                    "complaint": "CMP",
                    "transcript": "TRQ",
                }.get(vals.get("request_type", "enrollment_cert"), "SRV")
                seq = self.env["ir.sequence"].next_by_code("university.service.request") or fields.Date.today().strftime("%Y%m%d%H%M")
                vals["name"] = f"{prefix}-{seq}"
        return super().create(vals_list)

    def action_submit(self):
        self.ensure_one()
        self.write({"state": "pending"})
        self.message_post(body=_("Service request submitted."))

    def action_start_review(self):
        self.ensure_one()
        self.write({"state": "in_review", "reviewed_by_id": self.env.uid})

    def action_approve(self):
        self.ensure_one()
        self.write({"state": "approved", "reviewed_by_id": self.env.uid})

    def action_complete(self):
        self.ensure_one()
        self.write({
            "state": "completed",
            "reviewed_by_id": self.env.uid,
            "completed_at": fields.Datetime.now(),
        })
        self.message_post(body=_("Service request completed."))

    def action_reject(self):
        self.ensure_one()
        if not self.staff_notes:
            raise UserError(_("Please provide staff notes or reason before rejecting this request."))
        self.write({
            "state": "rejected",
            "reviewed_by_id": self.env.uid,
        })
        self.message_post(body=_("Service request rejected: %s") % self.staff_notes)
