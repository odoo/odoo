# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class L10n_PaResCityCorregimiento(models.Model):
    _name = 'l10n_pa.res.city.corregimiento'
    _description = 'Corregimiento'
    _order = 'name'

    name = fields.Char(required=True)
    city_id = fields.Many2one(
        comodel_name='res.city',
        string='District',
        required=True,
    )
    l10n_pa_code = fields.Char(
        string='DGI Code',
        required=True,
        help='This code will help with the identification of each corregimiento in Panama.',
    )

    _name_city_uniq = models.Constraint(
        'unique(city_id, name)',
        'The name of the corregimiento must be unique by district!',
    )
    _l10n_pa_code_uniq = models.Constraint(
        'unique(l10n_pa_code)',
        'The DGI code of the corregimiento must be unique!',
    )
