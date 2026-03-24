from odoo import fields, models


class TestFieldsMisc(models.Model):
    _name = 'test_fields.misc'
    _description = 'Test Fields Misc'

    json_default = fields.Json(default={'values': []})


class TestFieldsNumeric(models.Model):
    _name = 'test_fields.numeric'
    _description = 'Test Fields Numeric'

    float = fields.Float()
    float_digits = fields.Float(digits=(16, 2))


class TestFieldsTextual(models.Model):
    _name = 'test_fields.textual'
    _description = 'Test Fields Textual'

    char = fields.Char()
    text = fields.Text()
