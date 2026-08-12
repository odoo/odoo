from odoo import models, fields, api
from odoo.exceptions import ValidationError


class TestOrmInheritsPartner(models.Model):
    _name = 'test_orm.inherits.partner'
    _description = 'Test ORM Inherits Partner'

    name = fields.Char()
    email = fields.Char()


class TestOrmInheritsUsers(models.Model):
    _name = 'test_orm.inherits.users'
    _description = 'Test ORM Inherits Users'
    _inherits = {'test_orm.inherits.partner': 'partner_id'}

    name = fields.Char(related='partner_id.name', inherited=True, readonly=False)
    partner_id = fields.Many2one('test_orm.inherits.partner', required=True, ondelete='restrict')


class TestOrmInheritsUnit(models.Model):
    _name = 'test_orm.inherits.unit'
    _description = 'Test ORM Inherits Unit'

    name = fields.Char('Name', required=True, translate=True)
    state = fields.Selection([('a', 'A'), ('b', 'B')], string='State')
    surname = fields.Char(compute='_compute_surname')
    line_ids = fields.One2many('test_orm.inherits.unit_line', 'unit_id')
    readonly_name = fields.Char('Readonly Name', readonly=True)
    size = fields.Integer()

    @api.depends('name')
    def _compute_surname(self):
        for unit in self:
            unit.surname = unit.name or ''


class TestOrmInheritsUnitLine(models.Model):
    _name = 'test_orm.inherits.unit_line'
    _description = 'Test ORM Inherits Unit Line'

    name = fields.Char('Name', required=True)
    unit_id = fields.Many2one('test_orm.inherits.unit', required=True)


# We want to _inherits from the parent model and we add some fields


# in the child object
class TestOrmInheritsBox(models.Model):
    _name = 'test_orm.inherits.box'
    _inherits = {'test_orm.inherits.unit': 'unit_id'}
    _description = 'Test ORM Inherits Box'

    unit_id = fields.Many2one('test_orm.inherits.unit', 'Unit', required=True,
                              ondelete='cascade')
    field_in_box = fields.Char('Field1')
    size = fields.Integer()


# We add a third level of _inherits
class TestOrmInheritsPallet(models.Model):
    _name = 'test_orm.inherits.pallet'
    _inherits = {'test_orm.inherits.box': 'box_id'}
    _description = 'Test ORM Inherits Pallet'

    box_id = fields.Many2one('test_orm.inherits.box', 'Box', required=True,
                             ondelete='cascade')
    field_in_pallet = fields.Char('Field2')


# Another model for another test suite
class TestOrmInheritsAnotherUnit(models.Model):
    _name = 'test_orm.inherits.another_unit'
    _description = 'Test ORM Inherits Another Unit'

    val1 = fields.Integer('Value 1', required=True)
    ro_with_default = fields.Char(groups=fields.NO_ACCESS, default='roro')


# We want to _inherits from the parent model, add a field and check


# the new field is always equals to the first one
class TestOrmInheritsAnotherBox(models.Model):
    _name = 'test_orm.inherits.another_box'
    _inherits = {'test_orm.inherits.another_unit': 'another_unit_id'}
    _description = 'Test ORM Inherits Another Box'

    another_unit_id = fields.Many2one('test_orm.inherits.another_unit', 'Another Unit',
                                      required=True, ondelete='cascade')
    val2 = fields.Integer('Value 2', required=True)

    @api.constrains('val1', 'val2')
    def _check_values(self):
        if any(box.val1 != box.val2 for box in self):
            raise ValidationError("The two values must be equals")


class TestOrmInheritsUnstoredChild(models.Model):
    _name = "test_orm.inherits.unstored_child"
    _description = "Test ORM Inherits Unstored Child"

    contract_name = fields.Char()
    parent_id = fields.Many2one('test_orm.inherits.unstored_parent')
    unstored_shared_line_ids = fields.One2many(
        'test_orm.inherits.unstored_shared_line',
        'unstored_child_id',
        compute="_compute_unstored_shared_line_ids",
        store=True,
        readonly=False)

    @api.depends('contract_name')
    def _compute_unstored_shared_line_ids(self):
        for record in self:
            record.unstored_shared_line_ids = [(5, 0, 0), (0, 0, {
                'name': record.contract_name,
                'unstored_child_id': record.id,
            })]


class TestOrmInheritsUnstoredParent(models.Model):
    _name = "test_orm.inherits.unstored_parent"
    _inherits = {'test_orm.inherits.unstored_child': 'child_id'}
    _description = "Test ORM Inherits Unstored Parent"

    name = fields.Char()
    child_id = fields.Many2one(
        'test_orm.inherits.unstored_child',
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
            record.child_id = self.env['test_orm.inherits.unstored_child'].search([('parent_id', '=', record.id)], limit=1)

    def _search_child_id(self, operator, value):
        return []

    @api.model
    def _create(self, data_list):
        children = [vals['stored'].pop('child_id', None) for vals in data_list]
        result = super()._create(data_list)
        for (parent, child_id, vals) in zip(result, children, data_list):
            child = self.env['test_orm.inherits.unstored_child'].browse(child_id)
            child.parent_id = parent.id
            child.write({**vals.get('inherited', {})['test_orm.inherits.unstored_child'], 'parent_id': parent.id})
        return result


class TestOrmInheritsUnstoredSharedLine(models.Model):
    _name = "test_orm.inherits.unstored_shared_line"
    _description = "Test ORM Inherits Unstored Shared Line"

    name = fields.Char()
    unstored_child_id = fields.Many2one('test_orm.inherits.unstored_child')
