# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCountryGroup(models.Model):
    _inherit = 'res.country.group'

    def _active_languages(self):
        return self.env['res.lang'].search([]).ids

    show_line_subtotals_tax_selection = fields.Selection(
        string="Price display",
        selection=[
            ('tax_excluded', "Taxes excluded"),
            ('tax_included', "Taxes included"),
        ],
        required=True,
        default='tax_excluded',
    )
    language_ids = fields.Many2many(
        comodel_name='res.lang',
        string="Languages",
        default=_active_languages,
        required=True,
    )
