# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


# We just create a new model
class TestUnit(models.Model):
    _description = 'Test Unit'

    name = fields.Char('Name', required=True, translate=True)
    state = fields.Selection([('a', 'A'), ('b', 'B')], string='State')
    surname = fields.Char(compute='_compute_surname')
    line_ids = fields.One2many('test.unit.line', 'unit_id')
    readonly_name = fields.Char('Readonly Name', readonly=True)
    size = fields.Integer()

    @api.depends('name')
    def _compute_surname(self):
        for unit in self:
            unit.surname = unit.name or ''


class TestUnitLine(models.Model):
    _description = 'Test Unit Line'

    name = fields.Char('Name', required=True)
    unit_id = fields.Many2one('test.unit', required=True)


# We want to _inherits from the parent model and we add some fields


# in the child object
class TestBox(models.Model):
    _inherits = {'test.unit': 'unit_id'}
    _description = 'Test Box'

    unit_id = fields.Many2one('test.unit', 'Unit', required=True,
                              ondelete='cascade')
    field_in_box = fields.Char('Field1')
    size = fields.Integer()


# We add a third level of _inherits
class TestPallet(models.Model):
    _inherits = {'test.box': 'box_id'}
    _description = 'Test Pallet'

    box_id = fields.Many2one('test.box', 'Box', required=True,
                             ondelete='cascade')
    field_in_pallet = fields.Char('Field2')


# Another model for another test suite
class TestAnother_Unit(models.Model):
    _description = 'Another Test Unit'

    val1 = fields.Integer('Value 1', required=True)


# We want to _inherits from the parent model, add a field and check


# the new field is always equals to the first one
class TestAnother_Box(models.Model):
    _inherits = {'test.another_unit': 'another_unit_id'}
    _description = 'Another Test Box'

    another_unit_id = fields.Many2one('test.another_unit', 'Another Unit',
                                      required=True, ondelete='cascade')
    val2 = fields.Integer('Value 2', required=True)

    @api.constrains('val1', 'val2')
    def _check_values(self):
        if any(box.val1 != box.val2 for box in self):
            raise ValidationError("The two values must be equals")
