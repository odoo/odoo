from odoo.fields import Command
from odoo.http import request

from odoo.addons.website_hr_recruitment.controllers.main import WebsiteHrRecruitment


class WebsiteHrRecruitmentSkills(WebsiteHrRecruitment):

    def extract_data(self, model_sudo, values):
        if model_sudo.model != 'hr.applicant':
            return super().extract_data(model_sudo, values)

        values = dict(values)
        values.pop('applicant_skill_ids', None)
        skill_ids = {int(s) for s in values.pop('skill_ids', '').split(',') if s.strip().isdigit()}
        data = super().extract_data(model_sudo, values)
        if skill_ids:
            data['record']['applicant_skill_ids'] = [
                Command.create({
                    'skill_id': skill.id,
                    'skill_type_id': skill.skill_type_id.id,
                    'skill_level_id': self._get_default_skill_level(skill).id,
                })
                for skill in request.env['hr.skill'].sudo().browse(skill_ids).exists()
            ]
        return data

    def _get_default_skill_level(self, skill):
        levels = skill.skill_type_id.skill_level_ids
        return levels.filtered('default_level')[:1] or levels[:1]
