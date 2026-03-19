from odoo import fields, models


class TestJsonFieldDiscussion(models.Model):
    _name = 'test_json_field.discussion'
    _description = 'Test ORM Discussion'

    name = fields.Char(required=True)
    history = fields.Json('History', default={'delete_messages': []})
