# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCity(models.Model):
    _inherit = 'res.city'

    l10n_pa_code = fields.Char(string='DGI Code')

    _l10n_pa_code_uniq = models.Constraint(
        'unique(l10n_pa_code)',
        'The DGI code of the district must be unique!',
    )
