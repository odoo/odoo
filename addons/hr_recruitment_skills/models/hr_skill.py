from odoo import models


class HrSkill(models.Model):
    _inherit = 'hr.skill'

    def _compute_display_name(self):
        for skill in self:
            skill.display_name = f"{skill.skill_type_id.name}: {skill.name}"
