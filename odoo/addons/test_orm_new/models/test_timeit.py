from odoo import fields, models


class TestOrmTimeItSimpleMinded(models.Model):
    _name = 'test_orm.time_it.simple_minded'
    _description = 'test_orm.time_it.simple_minded'

    name = fields.Char()
    active = fields.Boolean(default=True)
    parent_id = fields.Many2one('test_orm.time_it.simple_minded')

    child_ids = fields.One2many('test_orm.time_it.simple_minded', 'parent_id')

    def simple_loop(self):
        for record in self:
            record.name

    def nested_loop(self):
        for record in self:
            for child in record.child_ids:
                child.name

    def union_once(self):
        """ Union all first children at once. """
        return self.browse().union(record.child_ids[:1] for record in self)

    def union_loop(self):
        """ Union all first children in a loop. """
        result = self.browse()
        for record in self:
            result |= record.child_ids[:1]
        return result
