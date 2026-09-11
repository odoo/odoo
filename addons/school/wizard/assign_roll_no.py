# See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AssignRollNo(models.TransientModel):
    """designed for assigning roll number to a student"""

    _name = "assign.roll.no"
    _description = "Assign Roll Number"

    standard_id = fields.Many2one("school.standard", "Class", required=True)
    medium_id = fields.Many2one("standard.medium", "Medium", required=True)

    def assign_rollno(self):
        """Method to assign roll no to students"""
        student_obj = self.env["student.student"]
        # Search Student
        for rec in self:
            # Assign roll no according to name.
            number = 1
            for student in student_obj.search(
                [
                    ("standard_id", "=", rec.standard_id.id),
                    ("medium_id", "=", rec.medium_id.id),
                ],
                order="name",
            ):
                student.write({"roll_no": number})
                number += 1
