from odoo import fields, models


class Test_Timeit_SimpleMinded(models.Model):
    _name = 'test_timeit.simple.minded'
    _description = 'test_timeit.simple.minded'

    name = fields.Char()
    active = fields.Boolean(default=True)
    parent_id = fields.Many2one('test_timeit.simple.minded')

    child_ids = fields.One2many('test_timeit.simple.minded', 'parent_id')
