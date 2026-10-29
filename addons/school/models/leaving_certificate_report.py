from odoo import _, api, models
from odoo.exceptions import ValidationError


class LeavingCertificateReport(models.AbstractModel):
    _name = "report.school.leaving_certificate"
    _description = "Leaving Certificate Result"

    @api.model
    def valid_student(self, student_ids):
        """Method to determine students who pass the exam"""
        for student in student_ids:
            if student.state not in ["terminate", "alumni"]:
                raise ValidationError(_("""Student is not alumni or terminated!."""))
            return student

    @api.model
    def _get_report_values(self, docids, data=None):
        student_ids = self.env["student.student"].browse(docids)
        return {
            "doc_ids": docids,
            "doc_model": self.env["student.student"],
            "data": data,
            "docs": student_ids,
            "valid_student": self.valid_student(student_ids),
        }
