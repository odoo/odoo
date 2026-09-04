# See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class TerminateReason(models.TransientModel):
    """Defining TransientModel to terminate reason."""

    _name = "terminate.reason"
    _description = "Terminate Reason"

    reason = fields.Text()
    leave_date = fields.Date(required=True, help="Enter student leave date")

    def save_terminate(self):
        """Method to terminate student and change state to terminate."""
        student_rec = self.env["student.student"].browse(self._context.get("active_id"))
        student_rec.write(
            {
                "state": "terminate",
                "terminate_reason": self.reason,
                "active": False,
                "leave_date": self.leave_date,
            }
        )
        student_rec.standard_id._compute_total_student()
        for rec in self.env["student.reminder"].search(
            [("stu_id", "=", student_rec.id)]
        ):
            rec.active = False
        if student_rec.user_id:
            student_rec.user_id.active = False
