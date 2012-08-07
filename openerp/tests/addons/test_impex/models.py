# -*- coding: utf-8 -*-
from openerp.osv import orm, fields

def selection_fn(obj, cr, uid, context=None):
    return list(enumerate(["Corge", "Grault", "Wheee", "Moog"]))

def function_fn(model, cr, uid, ids, field_name, arg, context):
    return dict((id, 3) for id in ids)
def function_fn_write(model, cr, uid, id, field_name, field_value, fnct_inv_arg, context):
    """ just so CreatorCase.export can be used
    """
    pass

models = [
    ('boolean', fields.boolean()),
    ('integer', fields.integer()),
    ('float', fields.float()),
    ('decimal', fields.float(digits=(16, 3))),
    ('string.bounded', fields.char('unknown', size=16)),
    ('string', fields.char('unknown', size=None)),
    ('date', fields.date()),
    ('datetime', fields.datetime()),
    ('text', fields.text()),
    ('selection', fields.selection([(1, "Foo"), (2, "Bar"), (3, "Qux")])),
    ('selection.function', fields.selection(selection_fn)),
    # just relate to an integer
    ('many2one', fields.many2one('export.integer')),
    ('one2many', fields.one2many('export.one2many.child', 'parent_id')),
    ('many2many', fields.many2many('export.many2many.other')),
    ('function', fields.function(function_fn, fnct_inv=function_fn_write, type="integer")),
    # related: specialization of fields.function, should work the same way
    # TODO: reference
]
for name, field in models:
    attrs = {
        '_name': 'export.%s' % name,
        '_columns': {
            'const': fields.integer(),
            'value': field
        },
        '_defaults': {'const': 4},
        'name_get': (lambda self, cr, uid, ids, context=None:
            [(record.id, "%s:%s" % (self._name, record.value))
             for record in self.browse(cr, uid, ids, context=context)]),
        'name_search': (lambda self, cr, uid, name, operator, context=None:
                self.name_get(cr, uid,
                    self.search(cr, uid, [['value', operator, int(name.split(':')[1])]])
                    , context=context)
                if isinstance(name, basestring) and name.split(':')[0] == self._name
                else [])
    }
    NewModel = type(
        'Export%s' % ''.join(section.capitalize() for section in name.split('.')),
        (orm.Model,),
        attrs)

class One2ManyChild(orm.Model):
    _name = 'export.one2many.child'
    # FIXME: orm.py:1161, fix to name_get on m2o field
    _rec_name = 'value'

    _columns = {
        'parent_id': fields.many2one('export.one2many'),
        'str': fields.char('unknown', size=None),
        'value': fields.integer()
    }
    def name_get(self, cr, uid, ids, context=None):
        return [(record.id, "%s:%s" % (self._name, record.value))
            for record in self.browse(cr, uid, ids, context=context)]

class One2ManyMultiple(orm.Model):
    _name = 'export.one2many.multiple'

    _columns = {
        'const': fields.integer(),
        'child1': fields.one2many('export.one2many.child.1', 'parent_id'),
        'child2': fields.one2many('export.one2many.child.2', 'parent_id'),
    }
    _defaults = { 'const': 36 }

class One2ManyChildMultiple(orm.Model):
    _name = 'export.one2many.multiple.child'
    # FIXME: orm.py:1161, fix to name_get on m2o field
    _rec_name = 'value'

    _columns = {
        'parent_id': fields.many2one('export.one2many.multiple'),
        'str': fields.char('unknown', size=None),
        'value': fields.integer()
    }
    def name_get(self, cr, uid, ids, context=None):
        return [(record.id, "%s:%s" % (self._name, record.value))
            for record in self.browse(cr, uid, ids, context=context)]
class One2ManyChild1(orm.Model):
    _name = 'export.one2many.child.1'
    _inherit = 'export.one2many.multiple.child'
class One2ManyChild2(orm.Model):
    _name = 'export.one2many.child.2'
    _inherit = 'export.one2many.multiple.child'

class Many2ManyChild(orm.Model):
    _name = 'export.many2many.other'
    # FIXME: orm.py:1161, fix to name_get on m2o field
    _rec_name = 'value'

    _columns = {
        'str': fields.char('unknown', size=None),
        'value': fields.integer()
    }
    def name_get(self, cr, uid, ids, context=None):
        return [(record.id, "%s:%s" % (self._name, record.value))
            for record in self.browse(cr, uid, ids, context=context)]
    def name_search(self, cr, user, name='', args=None, operator='ilike', context=None, limit=100):
        return (self.name_get(cr, user,
                    self.search(cr, user, [['value', operator, int(name.split(':')[1])]])
                    , context=context)
                if isinstance(name, basestring) and name.split(':')[0] == self._name
                else [])
