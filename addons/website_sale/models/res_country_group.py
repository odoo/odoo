# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCountryGroup(models.Model):
    _inherit = 'res.country.group'

    def _default_language_ids(self):
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
    # TODO-PDA: upgrade script default languages on existing groups
    language_ids = fields.Many2many('res.lang', default=_default_language_ids)
