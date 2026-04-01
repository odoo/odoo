# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


# We just create a new model
class TestUnit(models.Model):
    _name = 'test.unit'
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
    _name = 'test.unit.line'
    _description = 'Test Unit Line'

    name = fields.Char('Name', required=True)
    unit_id = fields.Many2one('test.unit', required=True)


# We want to _inherits from the parent model and we add some fields


# in the child object
class TestBox(models.Model):
    _name = 'test.box'
    _inherits = {'test.unit': 'unit_id'}
    _description = 'Test Box'

    unit_id = fields.Many2one('test.unit', 'Unit', required=True,
                              ondelete='cascade')
    field_in_box = fields.Char('Field1')
    size = fields.Integer()


# We add a third level of _inherits
class TestPallet(models.Model):
    _name = 'test.pallet'
    _inherits = {'test.box': 'box_id'}
    _description = 'Test Pallet'

    box_id = fields.Many2one('test.box', 'Box', required=True,
                             ondelete='cascade')
    field_in_pallet = fields.Char('Field2')


# Another model for another test suite
class TestAnother_Unit(models.Model):
    _name = 'test.another_unit'
    _description = 'Another Test Unit'

    val1 = fields.Integer('Value 1', required=True)


# We want to _inherits from the parent model, add a field and check


# the new field is always equals to the first one
class TestAnother_Box(models.Model):
    _name = 'test.another_box'
    _inherits = {'test.another_unit': 'another_unit_id'}
    _description = 'Another Test Box'

    another_unit_id = fields.Many2one('test.another_unit', 'Another Unit',
                                      required=True, ondelete='cascade')
    val2 = fields.Integer('Value 2', required=True)

    @api.constrains('val1', 'val2')
    def _check_values(self):
        if any(box.val1 != box.val2 for box in self):
            raise ValidationError("The two values must be equals")


class TestUnstoredInheritsChild(models.Model):
    _name = "test.unstored.inherits.child"
    _description = "Test Unstored Inherits Child"

    contract_name = fields.Char()
    parent_id = fields.Many2one('test.unstored.inherits.parent')
    test_unstored_inherits_shared_line_ids = fields.One2many(
        'test.unstored.inherits.shared.line',
        'test_unstored_inherits_child_id',
        compute="_compute_test_unstored_inherits_shared_line_ids",
        store=True,
        readonly=False)

    @api.depends('contract_name')
    def _compute_test_unstored_inherits_shared_line_ids(self):
        for record in self:
            record.test_unstored_inherits_shared_line_ids = [(5, 0, 0), (0, 0, {
                'name': record.contract_name,
                'test_unstored_inherits_child_id': record.id,
            })]


class TestUnstoredInheritsParent(models.Model):
    _name = "test.unstored.inherits.parent"
    _inherits = {'test.unstored.inherits.child': 'child_id'}
    _description = "Test Unstored Inherits Parent"

    name = fields.Char()
    child_id = fields.Many2one(
        'test.unstored.inherits.child',
        compute='_compute_child_id',
        search='_search_child_id',
        ondelete='cascade',
        required=True,
        store=False,
        compute_sudo=True,
        groups="hr.group_hr_user")

    @api.depends('name')
    def _compute_child_id(self):
        for record in self:
            record.child_id = self.env['test.unstored.inherits.child'].search([('parent_id', '=', record.id)], limit=1)

    def _search_child_id(self, operator, value):
        return []

    @api.model
    def _create(self, data_list):
        children = [vals['stored'].pop('child_id', None) for vals in data_list]
        result = super()._create(data_list)
        for (parent, child_id, vals) in zip(result, children, data_list):
            child = self.env['test.unstored.inherits.child'].browse(child_id)
            child.parent_id = parent.id
            child.write({**vals.get('inherited', {})['test.unstored.inherits.child'], 'parent_id': parent.id})
        return result


class TestUnstoredInheritsSharedLine(models.Model):
    _name = "test.unstored.inherits.shared.line"
    _description = "Test Unstored Inherits Shared Line"

    name = fields.Char()
    test_unstored_inherits_child_id = fields.Many2one('test.unstored.inherits.child')
