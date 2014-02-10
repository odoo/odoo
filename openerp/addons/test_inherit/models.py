# -*- coding: utf-8 -*-
import openerp

# We just create a new model
class mother(openerp.Model):
    _name = 'test.inherit.mother'

    name = openerp.fields.Char('Name', required=True)

# We want to inherits from the parent model and we add some fields
# in the child object
class daughter(openerp.Model):
    _name = 'test.inherit.daugther'
    _inherits = {'test.inherit.mother': 'template_id'}

    template_id = openerp.fields.Many2one('test.inherit.mother', 'Template',
                                          required=True, ondelete='cascade')
    field_in_daughter = openerp.fields.Char('Field1')


# We add a new field in the parent object. Because of a recent refactoring,
# this feature was broken.
# This test and these models try to show the bug and fix it.
class mother(openerp.Model):
    _inherit = 'test.inherit.mother'

    field_in_mother = openerp.fields.Char()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
