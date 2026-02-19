from odoo import api, models


class HrApplicant(models.Model):
    _inherit = 'hr.applicant'

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        result = super().fields_get(allfields, attributes)
        if skills := result.get('applicant_skill_ids'):
            skills['type'] = 'one2many_skill'

            skill_types = self.env["hr.skill.type"].search_read([], ["id", "display_name", "skill_ids"])
            all_skills = self.env["hr.skill"].search_read([], ["id", "display_name", "skill_type_id"])
            skill_map = {s["id"]: s for s in all_skills}

            for stype in skill_types:
                stype["skill_ids"] = [skill_map[sid] for sid in stype.get("skill_ids", []) if sid in skill_map]

            skills['skill_types'] = skill_types
            skills['selectedSkills'] = []
        return result
