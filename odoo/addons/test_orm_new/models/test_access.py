from odoo import fields, models


class TestOrmAccess(models.Model):
    _name = 'test_orm.access'
    _description = 'Test ORM Access'

    val = fields.Integer()
    categ_id = fields.Many2one('test_orm.access.category')
    parent_id = fields.Many2one('test_orm.access')


class TestOrmAccessCategory(models.Model):
    _name = 'test_orm.access.category'
    _description = "Test ORM Access category"

    name = fields.Char()
