# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class DecimalPrecisionTestModel(models.Model):
    _name = 'decimal.precision.test'

    float = fields.Float()
    float_2 = fields.Float(digits=(16, 2))
    float_4 = fields.Float(digits=(16, 4))
