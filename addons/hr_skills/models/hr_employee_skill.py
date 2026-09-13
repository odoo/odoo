from odoo import fields, models


class HrEmployeeSkill(models.Model):
    _name = "hr.employee.skill"
    _inherit = "mixin.hr.individual.skill"
    _description = "Skill level for employee"

    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        index=True,
        required=True,
        ondelete="cascade",
    )

    def _linked_field_name(self):
        return "employee_id"

    def open_hr_employee_skill_modal(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": "hr.employee.skill",
            "res_id": self.id if self else False,
            "target": "new",
            "context": {
                "show_employee": True,
                "default_skill_type_id": self.env["hr.skill.type"]
                ._get_certification_type()
                .id,
            },
            "views": [
                (
                    self.env.ref(
                        "hr_skills.employee_skill_view_inherit_certificate_form"
                    ).id,
                    "form",
                )
            ],
        }
