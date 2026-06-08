from odoo import api, fields, models


class ClearingLabel(models.Model):
    _name = 'clearing.label'
    _description = 'Bank Account Clearing Number Label'
    _order = 'country_id NULLS FIRST'
    _rec_names_search = ['name', 'country_id']

    name = fields.Char(required=True)
    country_id = fields.Many2one('res.country')
    country_code = fields.Char(related='country_id.code')

    @api.depends('name', 'country_id')
    @api.depends_context('formatted_display_name')
    def _compute_display_name(self):
        for label in self:
            if label.env.context.get('formatted_display_name') and label.country_id:
                label.display_name = f"{label.name} \v --{label.country_id.name}--"
            else:
                label.display_name = label.name
