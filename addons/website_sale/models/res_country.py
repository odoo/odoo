# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCountry(models.Model):
    _inherit = "res.country"

    tax_display = fields.Selection(
        string="eCommerce Price Display",
        selection=[("tax_included", "Taxes Included"), ("tax_excluded", "Taxes Excluded")],
    )
