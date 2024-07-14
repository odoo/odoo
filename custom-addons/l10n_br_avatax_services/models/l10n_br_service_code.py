# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class L10nBrServiceCode(models.Model):
    _name = "l10n_br.service.code"
    _description = "Product service codes defined by the city"
    _rec_name = "code"

    city_id = fields.Many2one(
        "res.city",
        string="City",
        required=True,
        help="The city this service code relates to.",
    )
    code = fields.Char(
        string="Service Code",
        required=True,
        help="The service code for this product as defined by the city.",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
        help="The company for which this code applies.",
    )
