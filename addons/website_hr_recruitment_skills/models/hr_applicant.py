from odoo import api, models


class HrApplicant(models.Model):
    _inherit = 'hr.applicant'

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        """ Expose `applicant_skill_ids` to the website form builder as a
        dedicated `one2many_skill` pseudo-type.

        The website form builder and the frontend both rely on the field type
        reported here:

        - the frontend renders a field with the `website.form_field_<type>`
          template, so the pseudo-type is what selects
          `website.form_field_one2many_skill` (a checkbox grid of the skills of
          the selected skill types, submitted through the `skill_ids` inputs)
          instead of the generic one2many widget;
        - `WebsiteForm._input_filters` maps that pseudo-type back to the
          regular one2many filter to sanitize the submitted values;
        - the form builder options read `skill_types` to list the available
          skill types (with their skills) in the sidebar, and `selectedSkills`
          to keep track of the skills of the selected types.
        """
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
