# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCity(models.Model):
    _inherit = 'res.city'

    l10n_us_county_id = fields.Many2one(
        comodel_name='l10n_us.res.county',
        string='County',
        domain="[('state_id', '=', state_id)]",
    )
