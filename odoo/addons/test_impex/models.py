# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

def selection_fn(model):
    return [(str(key), val) for key, val in enumerate(["Corge", "Grault", "Wheee", "Moog"])]

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
    ('selection', fields.Selection([(1, "Foo"), (2, "Bar"), (3, "Qux"), (4, '')])),
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
        const = fields.Integer(default=4)
        value = field

        @api.multi
        def name_get(self):
            return [(record.id, "%s:%s" % (self._name, record.value)) for record in self]

        @api.model
        def name_search(self, name='', args=None, operator='ilike', limit=100):
            if isinstance(name, basestring) and name.split(':')[0] == self._name:
                records = self.search([('value', operator, int(name.split(':')[1]))])
                return records.name_get()
            else:
                return []


class One2ManyChild(models.Model):
    _name = 'export.one2many.child'
    # FIXME: orm.py:1161, fix to name_get on m2o field
    _rec_name = 'value'

    parent_id = fields.Many2one('export.one2many')
    str = fields.Char()
    value = fields.Integer()

    @api.multi
    def name_get(self):
        return [(record.id, "%s:%s" % (self._name, record.value)) for record in self]

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if isinstance(name, basestring) and name.split(':')[0] == self._name:
            records = self.search([('value', operator, int(name.split(':')[1]))])
            return records.name_get()
        else:
            return []


class One2ManyMultiple(models.Model):
    _name = 'export.one2many.multiple'

    parent_id = fields.Many2one('export.one2many.recursive')
    const = fields.Integer(default=36)
    child1 = fields.One2many('export.one2many.child.1', 'parent_id')
    child2 = fields.One2many('export.one2many.child.2', 'parent_id')


class One2ManyChildMultiple(models.Model):
    _name = 'export.one2many.multiple.child'
    # FIXME: orm.py:1161, fix to name_get on m2o field
    _rec_name = 'value'

    parent_id = fields.Many2one('export.one2many.multiple')
    str = fields.Char()
    value = fields.Integer()

    @api.multi
    def name_get(self):
        return [(record.id, "%s:%s" % (self._name, record.value)) for record in self]


class One2ManyChild1(models.Model):
    _name = 'export.one2many.child.1'
    _inherit = 'export.one2many.multiple.child'


class One2ManyChild2(models.Model):
    _name = 'export.one2many.child.2'
    _inherit = 'export.one2many.multiple.child'


class Many2ManyChild(models.Model):
    _name = 'export.many2many.other'
    # FIXME: orm.py:1161, fix to name_get on m2o field
    _rec_name = 'value'

    str = fields.Char()
    value = fields.Integer()

    @api.multi
    def name_get(self):
        return [(record.id, "%s:%s" % (self._name, record.value)) for record in self]

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if isinstance(name, basestring) and name.split(':')[0] == self._name:
            records = self.search([('value', operator, int(name.split(':')[1]))])
            return records.name_get()
        else:
            return []


class SelectionWithDefault(models.Model):
    _name = 'export.selection.withdefault'

    const = fields.Integer(default=4)
    value = fields.Selection([(1, "Foo"), (2, "Bar")], default=2)


class RecO2M(models.Model):
    _name = 'export.one2many.recursive'

    value = fields.Integer()
    child = fields.One2many('export.one2many.multiple', 'parent_id')


class OnlyOne(models.Model):
    _name = 'export.unique'

    value = fields.Integer()

    _sql_constraints = [
        ('value_unique', 'unique (value)', "The value must be unique"),
    ]
