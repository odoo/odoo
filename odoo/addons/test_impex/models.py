# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

def selection_fn(self):
    return [
        (str(key), val)
        for key, val in enumerate([_("Corge"), _("Grault"), _("Wheee"), _("Moog")])
    ]

def compute_fn(records):
    for record in records:
        record.value = 3

def inverse_fn(records):
    pass

MODELS = [
    ('boolean', fields.Boolean()),
    ('integer', fields.Integer()),
    ('float', fields.Float()),
    ('decimal', fields.Float(digits=(16, 3))),
    ('string.bounded', fields.Char(size=16)),
    ('string.required', fields.Char(size=None, required=True)),
    ('string', fields.Char(size=None)),
    ('date', fields.Date()),
    ('datetime', fields.Datetime()),
    ('text', fields.Text()),
    ('selection', fields.Selection([('1', "Foo"), ('2', "Bar"), ('3', "Qux"), ('4', '')])),
    ('selection.function', fields.Selection(selection_fn)),
    # just relate to an integer
    ('many2one', fields.Many2one('export.integer')),
    ('one2many', fields.One2many('export.one2many.child', 'parent_id')),
    ('many2many', fields.Many2many('export.many2many.other')),
    ('function', fields.Integer(compute=compute_fn, inverse=inverse_fn)),
    # related: specialization of fields.function, should work the same way
    # TODO: reference
]

for name, field in MODELS:
    class NewModel(models.Model):
        _name = 'export.%s' % name
        _description = 'Export: %s' % name
        _rec_name = 'value'
        const = fields.Integer(default=4)
        value = field

        def _compute_display_name(self):
            for record in self:
                record.display_name = f"{self._name}:{record.value}"

        @api.model
        def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
            if isinstance(name, str) and name.split(':')[0] == self._name:
                return self._search([('value', operator, int(name.split(':')[1]))], limit=limit, order=order)
            else:
                return []

class One2ManyChild(models.Model):
    _name = 'export.one2many.child'
    _description = 'Export One to Many Child'
    # FIXME: orm.py:1161, fix to display_name on m2o field
    _rec_name = 'value'

    parent_id = fields.Many2one('export.one2many')
    str = fields.Char()
    m2o = fields.Many2one('export.integer')
    value = fields.Integer()

    def _compute_display_name(self):
        for record in self:
            record.display_name = f"{self._name}:{record.value}"

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        if isinstance(name, str) and name.split(':')[0] == self._name:
            return self._search([('value', operator, int(name.split(':')[1]))], limit=limit, order=order)
        else:
            return []


class One2ManyMultiple(models.Model):
    _name = 'export.one2many.multiple'
    _description = 'Export One To Many Multiple'
    _rec_name = 'parent_id'

    parent_id = fields.Many2one('export.one2many.recursive')
    const = fields.Integer(default=36)
    child1 = fields.One2many('export.one2many.child.1', 'parent_id')
    child2 = fields.One2many('export.one2many.child.2', 'parent_id')


class One2ManyChildMultiple(models.Model):
    _name = 'export.one2many.multiple.child'
    # FIXME: orm.py:1161, fix to display_name on m2o field
    _rec_name = 'value'
    _description = 'Export One To Many Multiple Child'

    parent_id = fields.Many2one('export.one2many.multiple')
    str = fields.Char()
    value = fields.Integer()

    def _compute_display_name(self):
        for record in self:
            record.display_name = f"{self._name}:{record.value}"


class One2ManyChild1(models.Model):
    _name = 'export.one2many.child.1'
    _inherit = 'export.one2many.multiple.child'
    _description = 'Export One to Many Child 1'


class One2ManyChild2(models.Model):
    _name = 'export.one2many.child.2'
    _inherit = 'export.one2many.multiple.child'
    _description = 'Export One To Many Child 2'


class Many2ManyChild(models.Model):
    _name = 'export.many2many.other'
    _description = 'Export Many to Many Other'
    # FIXME: orm.py:1161, fix to display_name on m2o field
    _rec_name = 'value'

    str = fields.Char()
    value = fields.Integer()

    def _compute_display_name(self):
        for record in self:
            record.display_name = f"{self._name}:{record.value}"

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        if isinstance(name, str) and name.split(':')[0] == self._name:
            return self._search([('value', operator, int(name.split(':')[1]))], limit=limit, order=order)
        else:
            return []


class SelectionWithDefault(models.Model):
    _name = 'export.selection.withdefault'
    _description = 'Export Selection With Default'

    const = fields.Integer(default=4)
    value = fields.Selection([('1', "Foo"), ('2', "Bar")], default='2')


class RecO2M(models.Model):
    _name = 'export.one2many.recursive'
    _description = 'Export One To Many Recursive'
    _rec_name = 'value'

    value = fields.Integer()
    child = fields.One2many('export.one2many.multiple', 'parent_id')


class OnlyOne(models.Model):
    _name = 'export.unique'
    _description = 'Export Unique'

    value = fields.Integer()
    value2 = fields.Integer()
    value3 = fields.Integer()

    _sql_constraints = [
        ('value_unique', 'unique (value)', "The value must be unique"),
        ('pair_unique', 'unique (value2, value3)', "The values must be unique"),
    ]

class InheritsParent(models.Model):
    _name = _description = 'export.inherits.parent'

    value_parent = fields.Integer()

class InheritsChild(models.Model):
    _name = _description = 'export.inherits.child'
    _inherits = {'export.inherits.parent': 'parent_id'}

    parent_id = fields.Many2one('export.inherits.parent', required=True, ondelete='cascade')
    value = fields.Integer()

class Many2String(models.Model):
    _name = _description = 'export.m2o.str'

    child_id = fields.Many2one('export.m2o.str.child')

class ChidToString(models.Model):
    _name = _description = 'export.m2o.str.child'

    name = fields.Char()

class WithRequiredField(models.Model):
    _name = _description = 'export.with.required.field'

    name = fields.Char()
    value = fields.Integer(required=True)

class Many2OneRequiredSubfield(models.Model):
    _name = _description = 'export.many2one.required.subfield'

    name = fields.Many2one('export.with.required.field')
