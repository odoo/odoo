import json

from odoo.http import request

from odoo.addons.website_hr_recruitment.controllers.main import WebsiteHrRecruitment


class WebsiteHrRecruitmentSkills(WebsiteHrRecruitment):

    # A real application form is a handful of checkboxes. Anything past this is
    # a crafted request, and every entry costs an hr.applicant.skill insert.
    _max_submitted_skills = 50

    def _handle_website_form(self, model_name, **kwargs):
        # This handler serves every form-enabled model, so without this guard a
        # submission to any other form carrying `skill_ids` would attach skills
        # to whatever record it had just created.
        if model_name != 'hr.applicant':
            return super()._handle_website_form(model_name, **kwargs)

        # The skill *type* checkboxes are submitted too, hidden and under the
        # field's own name, but hold nothing the applicant record needs.
        kwargs.pop('applicant_skill_ids', None)
        # dict.fromkeys drops duplicates while keeping the submitted order. Two
        # rows for one skill violate the "one active skill per skill_id" rule in
        # hr.individual.skill.mixin, and that rollback would take the whole
        # application with it.
        skill_ids = list(dict.fromkeys(
            int(s) for s in kwargs.pop('skill_ids', '').split(',') if s.strip().isdigit()
        ))[:self._max_submitted_skills]

        res = super()._handle_website_form(model_name, **kwargs)
        if not skill_ids:
            return res
        # super() answers with {'error': ...}, {'error_fields': ...} or plain
        # False on its failure paths, so there is not always an id to attach to.
        result = json.loads(res)
        if not isinstance(result, dict) or 'id' not in result:
            return res

        values = []
        for skill in request.env['hr.skill'].sudo().browse(skill_ids).exists():
            # `skill_level_id` is required and its compute on
            # `hr.individual.skill.mixin` only runs after the insert, so give it
            # the same value as the mixin would: the level flagged as
            # `default_level`, or the first one of the skill type.
            skill_level = (
                skill.skill_type_id.skill_level_ids.filtered('default_level')[:1]
                or skill.skill_type_id.skill_level_ids[:1]
            )
            values.append({
                'applicant_id': result['id'],
                'skill_id': skill.id,
                'skill_type_id': skill.skill_type_id.id,
                'skill_level_id': skill_level.id,
            })
        if values:
            request.env['hr.applicant.skill'].sudo().create(values)
        return res
