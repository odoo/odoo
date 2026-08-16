from odoo import fields, models


class TestOrmJsonField(models.Model):
    _name = 'test_orm.json_field'
    _description = 'Test ORM Json Field'

    value = fields.Json(default={'data': []})
