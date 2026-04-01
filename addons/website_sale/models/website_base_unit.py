# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class WebsiteBaseUnit(models.Model):
    _name = 'website.base.unit'
    _description = "Unit of Measure for price per unit on eCommerce products."
    _order = 'name'

    name = fields.Char(
        help="Define a custom unit to display in the price per unit of measure field.",
        required=True,
        translate=True,
    )
