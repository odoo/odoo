# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class DeliveryZipPrefix(models.Model):
    """Zip prefix that a delivery.carrier will deliver to."""

    _name = "delivery.zip.prefix"
    _description = "Delivery Zip Prefix"
    _order = "name, id"

    # we cannot easily convert a list of prefix names into upper to compare
    # with partner zips later on, so let's ensure they are always upper
    name = fields.Char(string="Prefix", required=True, clean=lambda name: name and name.upper())

    _name_uniq = models.Constraint("unique (name)", "Prefix already exists!")
