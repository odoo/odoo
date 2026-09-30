# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class L10n_PeResCityDistrict(models.Model):
    _name = 'l10n_pe.res.city.district'
    _description = 'District'
    _order = 'name'

    name = fields.Char(translate=True)
    city_id = fields.Many2one('res.city', 'City')
    code = fields.Char(
        help='This code will help with the identification of each district '
        'in Peru.')
