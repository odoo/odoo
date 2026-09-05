# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class L10n_PaResCityCorregimiento(models.Model):
    _name = 'l10n_pa.res.city.corregimiento'
    _description = 'Corregimiento'
    _order = 'name'

    name = fields.Char(translate=True)
    city_id = fields.Many2one(
        comodel_name='res.city',
        string='District',
    )
    l10n_pa_code = fields.Char(
        string='DGI Code',
        help='This code will help with the identification of each corregimiento in Panama.',
    )
