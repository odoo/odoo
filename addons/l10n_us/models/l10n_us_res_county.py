# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class L10nUsResCounty(models.Model):
    _name = 'l10n_us.res.county'
    _description = 'US County'
    _order = 'state_id, name'

    name = fields.Char(required=True)
    state_id = fields.Many2one(
        comodel_name='res.country.state',
        required=True,
        domain="[('country_id.code', '=', 'US')]",
    )
