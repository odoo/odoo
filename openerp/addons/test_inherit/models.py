# -*- coding: utf-8 -*-
from openerp import models, fields, api

# We just create a new model
class mother(models.Model):
    _name = 'test.inherit.mother'

    name = fields.Char('Name', required=True)
    surname = fields.Char(compute='_compute_surname')
    state = fields.Selection([('a', 'A'), ('b', 'B')])

    @api.one
    @api.depends('name')
    def _compute_surname(self):
        self.surname = self.name or ''

# We want to inherits from the parent model and we add some fields
# in the child object
class daughter(models.Model):
    _name = 'test.inherit.daughter'
    _inherits = {'test.inherit.mother': 'template_id'}

    template_id = fields.Many2one('test.inherit.mother', 'Template',
                                  required=True, ondelete='cascade')
    field_in_daughter = fields.Char('Field1')


# We add a new field in the parent object. Because of a recent refactoring,
# this feature was broken.
# This test and these models try to show the bug and fix it.
class mother(models.Model):
    _inherit = 'test.inherit.mother'

    field_in_mother = fields.Char()

    # extend the name field by adding a default value
    name = fields.Char(default='Unknown')

    # extend the selection of the state field
    state = fields.Selection(selection_add=[('c', 'C')])

    # override the computed field, and extend its dependencies
    @api.one
    @api.depends('field_in_mother')
    def _compute_surname(self):
        if self.field_in_mother:
            self.surname = self.field_in_mother
        else:
            super(mother, self)._compute_surname()


class mother(models.Model):
    _inherit = 'test.inherit.mother'

    # extend again the selection of the state field
    state = fields.Selection(selection_add=[('d', 'D')])


class daughter(models.Model):
    _inherit = 'test.inherit.daughter'

    # simply redeclare the field without adding any option
    template_id = fields.Many2one()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
