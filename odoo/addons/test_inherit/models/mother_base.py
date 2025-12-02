# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


# We create a new model, the name will be determined as 'test.inherit.mother'
class TestInheritMother(models.Model):
    _name = 'test.inherit.mother'
    _description = 'Test Inherit Mother'

    name = fields.Char(default='Foo')
    surname = fields.Char(compute='_compute_surname')

    @api.depends('name')
    def _compute_surname(self):
        for rec in self:
            rec.surname = rec.name or ''
