from odoo import fields, models


class TestOrmProperties(models.Model):
    _name = 'test_orm.properties'
    _description = 'Test ORM Properties'
    _inherit = 'properties.base.definition.mixin'

    name = fields.Char()
