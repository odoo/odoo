from odoo import fields, models


class TestFieldsMisc(models.Model):
    _name = 'test_fields.misc'
    _description = 'Test Fields Misc'

    json_default = fields.Json(default={'values': []})


class TestFieldsTextual(models.Model):
    _name = 'test_fields.textual'
    _description = 'Test Fields Textual'

    char = fields.Char()
    text = fields.Text()
