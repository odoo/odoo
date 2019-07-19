# Part of Odoo. See LICENSE file for full copyright and licensing details.
# Copyright 2019 Vauxoo (https://www.vauxoo.com) <info@vauxoo.com>

from odoo import fields, models


class City(models.Model):
    _inherit = "res.city"

    code = fields.Char(string='City Code', help='The city code.',
                       required=True)
