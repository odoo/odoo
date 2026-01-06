from odoo import api, models


class IrModel(models.Model):
    _inherit = 'ir.model'

    @api.model
    def get_authorized_fields(self, model_name, property_origins):
        """ Expose `applicant_skill_ids` to the website form builder as a
        dedicated `one2many_skill` pseudo-type.

        The website form builder and the frontend both rely on the field type
        reported here:

        - the frontend renders a field with the `website.form_field_<type>`
          template, so the pseudo-type is what selects
          `website.form_field_one2many_skill` (a checkbox grid of the skills of
          the selected skill types, submitted through the `skill_ids` inputs)
          instead of the generic one2many widget;
        - the form builder lists `records` (the active skill types) as the
          field's options in the sidebar, and the template reads `skill_types`
          to render the skills of the types selected there.

        This is done here rather than in `hr.applicant.fields_get` so that the
        pseudo-type stays confined to the form builder: the backend keeps
        seeing a plain one2many, and no extra query is made outside of the
        website.
        """
        result = super().get_authorized_fields(model_name, property_origins)
        if model_name != 'hr.applicant':
            return result
        if skills := result.get('applicant_skill_ids'):
            skills['type'] = 'one2many_skill'

            skills['skill_types'] = self.env['hr.skill.type'].web_search_read([], {
                'display_name': {},
                'skill_ids': {'fields': {'display_name': {}}},
            })['records']
            skills['records'] = [
                {'id': skill_type['id'], 'display_name': skill_type['display_name']}
                for skill_type in skills['skill_types']
            ]
        return result
