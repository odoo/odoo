from odoo import api, models, fields


class AvataxExemption(models.Model):
    _name = 'avatax.exemption'
    _description = "Avatax Partner Exemption Codes"
    _rec_names_search = ['name', 'code']

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    description = fields.Char()
    valid_country_ids = fields.Many2many('res.country')
    company_id = fields.Many2one('res.company', required=True)

    @api.depends('code')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f'[{record.code}] {record.name}'
