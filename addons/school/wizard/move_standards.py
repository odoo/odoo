# See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models
from odoo.exceptions import ValidationError


class MoveStandards(models.TransientModel):
    """Defining TransientModel to move standard."""

    _name = "move.standards"
    _description = "Move Standards"

    academic_year_id = fields.Many2one(
        "academic.year",
        "Academic Year",
        required=True,
        help="""
The Acedemic year from which you need to move the student to next Year.""",
    )

    def move_start(self):
        """Code for moving student to next standard"""
        academic_obj = self.env["academic.year"]
        school_stand_obj = self.env["school.standard"]
        standard_obj = self.env["standard.standard"]
        student_obj = self.env["student.student"]
        next_year_id = academic_obj.next_year(self.academic_year_id.sequence)

        if not next_year_id:
            raise ValidationError(
                _(
                    "The next sequanced Acedemic year after the selected "
                    "one is not configured!"
                )
            )
        done_rec = student_obj.search(
            [("state", "=", "done"), ("year", "=", self.academic_year_id.id)]
        )
        for stud in done_rec:
            standard_seq = stud.standard_id.standard_id.sequence
            next_class_id = standard_obj.next_standard(standard_seq)
            # Assign the academic year
            if next_class_id:
                division = stud.standard_id.division_id.id or False
                next_stand = school_stand_obj.search(
                    [
                        ("standard_id", "=", next_class_id.id),
                        ("division_id", "=", division),
                        ("school_id", "=", stud.school_id.id),
                        ("medium_id", "=", stud.medium_id.id),
                    ]
                )
                if next_stand:
                    std_vals = {
                        "year": next_year_id,
                        "standard_id": next_stand.id,
                    }
                    # Move student to next standard
                    stud.write(std_vals)
