import json

from odoo.http import request

from odoo.addons.website_hr_recruitment.controllers.main import WebsiteHrRecruitment


class WebsiteHrRecruitmentSkills(WebsiteHrRecruitment):

    def _handle_website_form(self, model_name, **kwargs):
        skills = ''
        if kwargs.get('applicant_skill_ids') and kwargs.get('skill_ids'):
            kwargs.pop('applicant_skill_ids')
            skills = kwargs.pop('skill_ids')
        res = super()._handle_website_form(model_name, **kwargs)
        for skill in [int(s) for s in skills.split(',') if s.strip()]:
            skill_type_id = request.env['hr.skill'].sudo().browse(skill).skill_type_id
            request.env['hr.applicant.skill'].sudo().create({
                'skill_id': skill,
                'skill_level_id': skill_type_id.skill_level_ids[:1].id,
                'applicant_id': json.loads(res)['id'],
                'skill_type_id': skill_type_id.id,
                })
        return res
