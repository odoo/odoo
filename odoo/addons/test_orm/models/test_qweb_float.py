from odoo import fields, models


class TestQwebFloatDecimalPrecisionTest(models.Model):
    _name = 'test_qweb_float.decimal.precision.test'
    _description = 'Decimal Precision Test'

    float = fields.Float()
    float_2 = fields.Float(digits=(16, 2))
