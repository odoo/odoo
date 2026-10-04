# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class L10n_PaResCityCorregimientoPoblado(models.Model):
    _name = 'l10n_pa.res.city.corregimiento.poblado'
    _description = 'Poblado'
    _order = 'name'

    name = fields.Char(required=True)
    corregimiento_id = fields.Many2one(
        comodel_name='l10n_pa.res.city.corregimiento',
        string='Corregimiento',
        required=True,
    )
    l10n_pa_code = fields.Char(
        string='DGI Code',
        required=True,
        help='This code will help with the identification of each poblado in Panama.',
    )
    boundary = fields.Text(
        help='GeoJSON geometry ({"type": ..., "coordinates": ...}) of the poblado '
             'boundary, used to resolve a Panama postal code to its poblado. Not '
             'every poblado has one in the official dataset.',
    )

    # Note: the poblado name is not guaranteed unique within a corregimiento (the
    # official DGI dataset has distinct, separately-coded populated places that
    # share a name). The DGI code is the actual unique identifier.
    _l10n_pa_code_uniq = models.Constraint(
        'unique(l10n_pa_code)',
        'The DGI code of the poblado must be unique!',
    )
