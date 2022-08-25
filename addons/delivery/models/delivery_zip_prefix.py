# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class DeliveryZipPrefix(models.Model):
    """ Zip prefix that a delivery.carrier will deliver to. """
    _name = 'delivery.zip.prefix'
    _description = 'Delivery Zip Prefix'
    _order = 'name, id'

    name = fields.Char('Prefix', required=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # we cannot easily convert a list of prefix names into upper to compare with partner zips
            # later on, so let's ensure they are always upper
            vals['name'] = vals['name'].upper()
        return super(DeliveryZipPrefix, self).create(vals_list)

    def write(self, vals):
        vals['name'] = vals['name'].upper()
        return super().write(vals)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Prefix already exists!"),
    ]
