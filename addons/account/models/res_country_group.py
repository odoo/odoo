# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCountryGroup(models.Model):
    _inherit = 'res.country.group'

    exclude_state_ids = fields.Many2many(
        comodel_name='res.country.state',
        string="Fiscal Exceptions",
        help="Those states are ignored by the fiscal positions")
