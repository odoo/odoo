from odoo import api, fields, models


class L10n_CrResCityDistrict(models.Model):
    _name = 'l10n_cr.res.city.district'
    _description = 'District'
    _order = 'name'

    name = fields.Char(required=True)
    city_id = fields.Many2one(comodel_name='res.city', string='Cantón', required=True)
    code = fields.Char(size=2, help='Two-digit district code within its cantón.', required=True)

    _city_code_unique = models.UniqueIndex('(city_id, code)', "The district code must be unique within its cantón.")

    @api.depends_context('formatted_display_name')
    @api.depends('name', 'city_id.name')
    def _compute_display_name(self):
        for district in self:
            if self.env.context.get('formatted_display_name'):
                district.display_name = f'{district.name} \v--{district.city_id.name}--'
            else:
                district.display_name = f'{district.name} ({district.city_id.name})'
