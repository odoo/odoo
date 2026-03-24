from odoo import fields, models


class TestCreateMixed(models.Model):
    _name = 'test_create.mixed'
    _description = 'Test ORM Mixed'

    foo = fields.Char()
    text = fields.Text()