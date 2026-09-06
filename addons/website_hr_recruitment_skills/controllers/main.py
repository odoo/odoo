import json

from odoo.http import request

from odoo.addons.website_hr_recruitment.controllers.main import WebsiteHrRecruitment


class WebsiteHrRecruitmentSkills(WebsiteHrRecruitment):

    def _handle_website_form(self, model_name, **kwargs):
        kwargs.pop('applicant_skill_ids', None)
        skill_ids = [int(s) for s in kwargs.pop('skill_ids', '').split(',') if s.strip().isdigit()]
        res = super()._handle_website_form(model_name, **kwargs)
        if skill_ids:
            skills = request.env['hr.skill'].sudo().browse(skill_ids).exists()
            applicant_id = json.loads(res)['id']
            # `skill_level_id` is required and its compute on
            # `hr.individual.skill.mixin` only runs after the insert, so give it
            # the same value as the mixin would: the level flagged as
            # `default_level`, or the first one of the skill type.
            request.env['hr.applicant.skill'].sudo().create([{
                'applicant_id': applicant_id,
                'skill_id': skill.id,
                'skill_type_id': skill.skill_type_id.id,
                'skill_level_id': (
                    skill.skill_type_id.skill_level_ids.filtered('default_level')[:1]
                    or skill.skill_type_id.skill_level_ids[:1]
                ).id,
            } for skill in skills])
        return res
