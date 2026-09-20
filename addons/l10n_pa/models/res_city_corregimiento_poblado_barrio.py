# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class L10n_PaResCityCorregimientoPobladoBarrio(models.Model):
    _name = 'l10n_pa.res.city.corregimiento.poblado.barrio'
    _description = 'Barrio'
    _order = 'name'

    name = fields.Char(required=True)
    poblado_id = fields.Many2one(
        comodel_name='l10n_pa.res.city.corregimiento.poblado',
        string='Poblado',
        required=True,
    )
    l10n_pa_code = fields.Char(
        string='DGI Code',
        required=True,
        help='This code will help with the identification of each barrio in Panama.',
    )
    boundary = fields.Text(
        help='GeoJSON geometry ({"type": ..., "coordinates": ...}) of the barrio '
             'boundary, used to resolve a Panama postal code to its barrio.',
    )

    # Note: not enforcing name uniqueness within a poblado, consistent with the
    # poblado model - the DGI code is the actual unique identifier in this dataset.
    _l10n_pa_code_uniq = models.Constraint(
        'unique(l10n_pa_code)',
        'The DGI code of the barrio must be unique!',
    )
