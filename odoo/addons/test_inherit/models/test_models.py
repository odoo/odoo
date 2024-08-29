# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons import test_new_api, base, test_inherit

from odoo import models, fields, api


# We inherit from the parent model, and we add some fields in the child model
class TestInheritDaughter(models.Model, test_inherit.TestInheritDaughter):
    _name = 'test_inherit_daughter'
    _description = 'Test Inherit Daughter'

    template_id = fields.Many2one('test.inherit.mother', 'Template',
                                  delegate=True, required=True, ondelete='cascade')
    field_in_daughter = fields.Char('Field1')


# pylint: disable=E0102
class TestInheritDaughter(models.Model, test_inherit.TestInheritDaughter):
    _name = 'test_inherit_daughter'

    # simply redeclare the field without adding any option
    template_id = fields.Many2one()

    # change the default value of an inherited field
    name = fields.Char(default='Baz')


class ResPartner(models.Model, base.ResPartner):

    # define a one2many field based on the inherited field partner_id
    daughter_ids = fields.One2many('test_inherit_daughter', 'partner_id', string="My daughter_ids")


# Check the overriding of property fields by non-property fields.
# Contribution by Adrien Peiffer (ACSONE).
class TestInheritProperty(models.Model, test_inherit.TestInheritProperty):
    _name = 'test_inherit_property'
    _description = 'Test Inherit Property'

    name = fields.Char('Name', required=True)
    property_foo = fields.Integer(string='Foo', company_dependent=True)
    property_bar = fields.Integer(string='Bar', company_dependent=True)


class TestInheritProperty(models.Model, test_inherit.TestInheritProperty):
    _name = 'test_inherit_property'

    # override property_foo with a plain normal field
    property_foo = fields.Integer(company_dependent=False)

    # override property_bar with a new-api computed field
    property_bar = fields.Integer(compute='_compute_bar', company_dependent=False)

    def _compute_bar(self):
        for record in self:
            record.property_bar = 42


#
# Extend a parent model after is has been inherited in a child model
#
class TestInheritParent(models.AbstractModel, test_inherit.TestInheritParent):
    _name = 'test_inherit_parent'
    _description = 'Test Inherit Parent'

    def stuff(self):
        return 'P1'


class TestInheritChild(models.AbstractModel, test_inherit.TestInheritParent):
    _name = 'test_inherit_child'
    _description = 'Test Inherit Child'

    bar = fields.Integer()

    def stuff(self):
        return super().stuff() + 'C1'


# pylint: disable=E0102
class TestInheritParent(models.AbstractModel, test_inherit.TestInheritParent):
    _name = 'test_inherit_parent'

    foo = fields.Integer()

    _sql_constraints = [('unique_foo', 'UNIQUE(foo)', 'foo must be unique')]

    def stuff(self):
        return super().stuff() + 'P2'

    @api.constrains('foo')
    def _check_foo(self):
        pass


#
# Extend a selection field
#
class TestNewApiSelection(models.Model, test_new_api.TestNewApiSelection):
    _name = 'test_new_api.selection'

    state = fields.Selection(selection_add=[('bar', 'Bar'), ('baz', 'Baz')])
    other = fields.Selection('_other_values')

    def _other_values(self):
        return [('baz', 'Baz')]


#
# Helper model used in test_inherit_depends
#
class TestInheritMixin(models.AbstractModel):
    _name = 'test_inherit_mixin'
    _description = "Test Inherit Mixin"

    published = fields.Boolean()


class TestNewApiMessage(models.Model, test_new_api.TestNewApiMessage):
    _name = 'test_new_api.message'

    body = fields.Text(translate=True)  # Test conversion of char (with trigram indexed) to jsonb postgreSQL type

    def bar(self):
        return 1
