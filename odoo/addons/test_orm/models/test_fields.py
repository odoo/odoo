from odoo import fields, models


class TestFieldsMisc(models.Model):
    _name = 'test_fields.misc'
    _description = 'Test Fields Misc'

    json_default = fields.Json(default={'values': []})
