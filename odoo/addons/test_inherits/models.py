# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


# We just create a new model
class Unit(models.Model):
    _name = 'test.unit'
    _description = 'Test Unit'

    name = fields.Char('Name', required=True)
    state = fields.Selection([('a', 'A'), ('b', 'B')], string='State')
    surname = fields.Char(compute='_compute_surname')

    @api.depends('name')
    def _compute_surname(self):
        for unit in self:
            unit.surname = unit.name or ''


# We want to _inherits from the parent model and we add some fields
# in the child object
class Box(models.Model):
    _name = 'test.box'
    _inherits = {'test.unit': 'unit_id'}
    _description = 'Test Box'

    unit_id = fields.Many2one('test.unit', 'Unit', required=True,
                              ondelete='cascade')
    field_in_box = fields.Char('Field1')


# We add a third level of _inherits
class Pallet(models.Model):
    _name = 'test.pallet'
    _inherits = {'test.box': 'box_id'}
    _description = 'Test Pallet'

    box_id = fields.Many2one('test.box', 'Box', required=True,
                             ondelete='cascade')
    field_in_pallet = fields.Char('Field2')


# Another model for another test suite
class AnotherUnit(models.Model):
    _name = 'test.another_unit'
    _description = 'Another Test Unit'

    val1 = fields.Integer('Value 1', required=True)


# We want to _inherits from the parent model, add a field and check
# the new field is always equals to the first one
class AnotherBox(models.Model):
    _name = 'test.another_box'
    _inherits = {'test.another_unit': 'another_unit_id'}
    _description = 'Another Test Box'

    another_unit_id = fields.Many2one('test.another_unit', 'Another Unit',
                                      required=True, ondelete='cascade')
    val2 = fields.Integer('Value 2', required=True)

    @api.constrains('val1', 'val2')
    def _check(self):
        if self.val1 != self.val2:
            raise ValidationError("The two values must be equals")
