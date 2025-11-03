from odoo import fields, models


class Test_Qweb_Float_DecimalPrecision(models.Model):
    _name = 'test_qweb_float.decimal_precision'
    _description = 'Decimal Precision Test'

    float = fields.Float()
    float_2 = fields.Float(digits=(16, 2))
    float_4 = fields.Float(digits=(16, 4))
