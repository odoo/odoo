from odoo import api, fields, models


class TestTimeitSimpleMinded(models.Model):
    _name = 'test_timeit.simple.minded'
    _description = 'test_timeit.simple.minded'

    name = fields.Char()
    active = fields.Boolean(default=True)
    parent_id = fields.Many2one('test_timeit.simple.minded')

    child_ids = fields.One2many('test_timeit.simple.minded', 'parent_id')

    def simple_loop(self):
        for record in self:
            record.name

    def nested_loop(self):
        for record in self:
            for child in record.child_ids:
                child.name

    def union_once(self):
        """ Union all first children at once. """
        return self.browse().union(*[record.child_ids[:1] for record in self])

    def union_loop(self):
        """ Union all first children in a loop. """
        result = self.browse()
        for record in self:
            result |= record.child_ids[:1]
        return result
