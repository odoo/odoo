# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api

# We create a new model
class mother(models.Model):
    _name = 'test.inherit.mother'
    _description = 'Test Inherit Mother'

    name = fields.Char(default='Foo')
    state = fields.Selection([('a', 'A'), ('b', 'B')], default='a')
    surname = fields.Char(compute='_compute_surname')

    @api.depends('name')
    def _compute_surname(self):
        for rec in self:
            rec.surname = rec.name or ''


# We inherit from the parent model, and we add some fields in the child model
class daughter(models.Model):
    _name = 'test.inherit.daughter'
    _description = 'Test Inherit Daughter'

    template_id = fields.Many2one('test.inherit.mother', 'Template',
                                  delegate=True, required=True, ondelete='cascade')
    field_in_daughter = fields.Char('Field1')


# We add a new field in the parent model. Because of a recent refactoring, this
# feature was broken. These models rely on that feature.
class mother(models.Model):
    _inherit = 'test.inherit.mother'

    field_in_mother = fields.Char()
    partner_id = fields.Many2one('res.partner')

    # extend the name field: make it required and change its default value
    name = fields.Char(required=True, default='Bar')

    # extend the selection of the state field, and discard its default value
    state = fields.Selection(selection_add=[('c', 'C')], default=None)

    # override the computed field, and extend its dependencies
    @api.depends('field_in_mother')
    def _compute_surname(self):
        for rec in self:
            if rec.field_in_mother:
                rec.surname = rec.field_in_mother
            else:
                super(mother, rec)._compute_surname()


class mother(models.Model):
    _inherit = 'test.inherit.mother'

    # extend again the selection of the state field
    state = fields.Selection(selection_add=[('d', 'D')])


class daughter(models.Model):
    _inherit = 'test.inherit.daughter'

    # simply redeclare the field without adding any option
    template_id = fields.Many2one()

    # change the default value of an inherited field
    name = fields.Char(default='Baz')


class res_partner(models.Model):
    _inherit = 'res.partner'

    # define a one2many field based on the inherited field partner_id
    daughter_ids = fields.One2many('test.inherit.daughter', 'partner_id')


# Check the overriding of property fields by non-property fields.
# Contribution by Adrien Peiffer (ACSONE).
class test_inherit_property(models.Model):
    _name = 'test.inherit.property'
    _description = 'Test Inherit Property'

    name = fields.Char('Name', required=True)
    property_foo = fields.Integer(string='Foo', company_dependent=True)
    property_bar = fields.Integer(string='Bar', company_dependent=True)


class test_inherit_property(models.Model):
    _inherit = 'test.inherit.property'

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
class Parent1(models.AbstractModel):
    _name = 'test.inherit.parent'
    _description = 'Test Inherit Parent'

    def stuff(self):
        return 'P1'


class Child(models.AbstractModel):
    _name = 'test.inherit.child'
    _inherit = 'test.inherit.parent'
    _description = 'Test Inherit Child'

    bar = fields.Integer()

    def stuff(self):
        return super(Child, self).stuff() + 'C1'


class Parent2(models.AbstractModel):
    _inherit = 'test.inherit.parent'

    foo = fields.Integer()

    _sql_constraints = [('unique_foo', 'UNIQUE(foo)', 'foo must be unique')]

    def stuff(self):
        return super(Parent2, self).stuff() + 'P2'

    @api.constrains('foo')
    def _check_foo(self):
        pass
