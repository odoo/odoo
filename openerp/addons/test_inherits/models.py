# -*- coding: utf-8 -*-
from openerp import models, fields, api, osv


# We just create a new model
class Unit(models.Model):
    _name = 'test.unit'

    _columns = {
        'name': osv.fields.char('Name', required=True),
        'state': osv.fields.selection([('a', 'A'), ('b', 'B')],
                                      string='State'),
    }

    surname = fields.Char(compute='_compute_surname')

    @api.one
    @api.depends('name')
    def _compute_surname(self):
        self.surname = self.name or ''


# We want to _inherits from the parent model and we add some fields
# in the child object
class Box(models.Model):
    _name = 'test.box'
    _inherits = {'test.unit': 'unit_id'}

    unit_id = fields.Many2one('test.unit', 'Unit', required=True,
                              ondelete='cascade')
    field_in_box = fields.Char('Field1')


# We add a third level of _inherits
class Pallet(models.Model):
    _name = 'test.pallet'
    _inherits = {'test.box': 'box_id'}

    box_id = fields.Many2one('test.box', 'Box', required=True,
                             ondelete='cascade')
    field_in_pallet = fields.Char('Field2')
