from odoo import api, fields, models


class BenchmarkFixture(models.Model):
    _name = 'test_testing_utilities.benchmark'
    _description = 'Benchmark cleanup fixture'

    value = fields.Integer()
    double = fields.Integer(compute='_compute_double', store=True)

    @api.depends('value')
    def _compute_double(self):
        for record in self:
            record.double = record.value * 2
