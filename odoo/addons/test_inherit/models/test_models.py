# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.addons import web, test_new_api, test_inherit


# We inherit from the parent model, and we add some fields in the child model
class Test_Inherit_Daughter(models.Model):
    _description = 'Test Inherit Daughter'

    template_id = fields.Many2one('test.inherit.mother', 'Template',
                                  delegate=True, required=True, ondelete='cascade')
    field_in_daughter = fields.Char('Field1')


# pylint: disable=E0102
class Test_Inherit_Daughter(models.Model, test_inherit.Test_Inherit_Daughter):  # noqa: F811

    # simply redeclare the field without adding any option
    template_id = fields.Many2one()

    # change the default value of an inherited field
    name = fields.Char(default='Baz')


class ResPartner(web.ResPartner):

    # define a one2many field based on the inherited field partner_id (from test.inherit.mother, with template_id)
    daughter_ids = fields.One2many('test_inherit_daughter', 'partner_id', string="My daughter_ids")


# Check the overriding of property fields by non-property fields.


# Contribution by Adrien Peiffer (ACSONE).
class Test_Inherit_Property(models.Model):
    _description = 'Test Inherit Property'

    name = fields.Char('Name', required=True)
    property_foo = fields.Integer(string='Foo', company_dependent=True)
    property_bar = fields.Integer(string='Bar', company_dependent=True)


# pylint: disable=E0102
class Test_Inherit_Property(models.Model, test_inherit.Test_Inherit_Property):  # noqa: F811

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


class Test_Inherit_Parent(models.AbstractModel):
    _description = 'Test Inherit Parent'

    def stuff(self):
        return 'P1'


class Test_Inherit_Child(models.AbstractModel, test_inherit.Test_Inherit_Parent):
    _description = 'Test Inherit Child'

    bar = fields.Integer()

    def stuff(self):
        return super().stuff() + 'C1'


# pylint: disable=E0102
class Test_Inherit_Parent(models.AbstractModel, test_inherit.Test_Inherit_Parent):  # noqa: F811

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


class Test_New_ApiSelection(test_new_api.Test_New_ApiSelection):

    state = fields.Selection(selection_add=[('bar', 'Bar'), ('baz', 'Baz')])
    other = fields.Selection('_other_values')

    def _other_values(self):
        return [('baz', 'Baz')]


#
# Helper model used in test_inherit_depends
#


class Test_Inherit_Mixin(models.AbstractModel):
    _description = "Test Inherit Mixin"

    published = fields.Boolean()


class Test_New_ApiMessage(test_new_api.Test_New_ApiMessage):

    body = fields.Text(translate=True)  # Test conversion of char (with trigram indexed) to jsonb postgreSQL type

    def bar(self):
        return 1
