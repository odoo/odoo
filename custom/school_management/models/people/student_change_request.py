# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class UniversityStudentChangeRequest(models.Model):
    _name = "university.student.change.request"
    _description = "Student Profile Information Change Request"
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
    request_date = fields.Date(
        string="Request Date",
        default=fields.Date.context_today,
        readonly=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("pending", "Pending Approval"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        string="Status",
        default="draft",
        tracking=True,
    )

    # Requested Changes
    proposed_name = fields.Char(string="Proposed Latin Name")
    proposed_name_khmer = fields.Char(string="Proposed Khmer / Local Name")
    proposed_email = fields.Char(string="Proposed Email")
    proposed_phone = fields.Char(string="Proposed Phone")
    proposed_address = fields.Text(string="Proposed Address")
    proposed_emergency_name = fields.Char(string="Proposed Emergency Contact Name")
    proposed_emergency_phone = fields.Char(string="Proposed Emergency Contact Phone")

    reason = fields.Text(
        string="Reason for Change",
        required=True,
        help="Explain the justification for updating official student records.",
    )
    supporting_document = fields.Binary(
        string="Supporting Document (ID Card, Certificate, Affidavit)",
    )
    supporting_document_name = fields.Char(string="Document Filename")

    # Staff Approval / Rejection
    rejection_reason = fields.Text(string="Staff Rejection Reason", tracking=True)
    reviewed_by_id = fields.Many2one("res.users", string="Reviewed By", readonly=True)
    reviewed_at = fields.Datetime(string="Reviewed At", readonly=True)

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
                vals["name"] = self.env["ir.sequence"].next_by_code("university.student.change.request") or _("REQ-%s") % fields.Date.today().strftime("%Y%m%d")
        return super().create(vals_list)

    def action_submit(self):
        self.ensure_one()
        self.write({"state": "pending"})
        self.message_post(body=_("Profile change request submitted for review."))

    def action_approve(self):
        self.ensure_one()
        student = self.student_id
        update_vals = {}
        if self.proposed_name:
            update_vals["name"] = self.proposed_name
        if self.proposed_name_khmer:
            update_vals["name_khmer"] = self.proposed_name_khmer
        if self.proposed_email:
            update_vals["email"] = self.proposed_email
        if self.proposed_phone:
            update_vals["phone"] = self.proposed_phone
        if self.proposed_address:
            update_vals["address"] = self.proposed_address
        if self.proposed_emergency_name:
            update_vals["emergency_contact_name"] = self.proposed_emergency_name
        if self.proposed_emergency_phone:
            update_vals["emergency_contact_phone"] = self.proposed_emergency_phone

        if update_vals:
            student.sudo().write(update_vals)

        self.write({
            "state": "approved",
            "reviewed_by_id": self.env.uid,
            "reviewed_at": fields.Datetime.now(),
        })
        self.message_post(body=_("Profile change request approved and student record updated."))

    def action_reject(self):
        self.ensure_one()
        if not self.rejection_reason:
            raise UserError(_("Please provide a rejection reason before rejecting the request."))
        self.write({
            "state": "rejected",
            "reviewed_by_id": self.env.uid,
            "reviewed_at": fields.Datetime.now(),
        })
        self.message_post(body=_("Profile change request rejected: %s") % self.rejection_reason)
