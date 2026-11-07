from odoo import models


class HrSkillType(models.Model):
    _inherit = 'hr.skill.type'

    def _get_skill_models(self):
        return super()._get_skill_models() + ['hr.applicant.skill']
