from openerp.osv import orm, fields

def name(n): return 'base_import.tests.models.%s' % n

class char(orm.Model):
    _name = name('char')

    _columns = {
        'value': fields.char('unknown')
    }

class char_required(orm.Model):
    _name = name('char.required')

    _columns = {
        'value': fields.char('unknown', required=True)
    }

class char_readonly(orm.Model):
    _name = name('char.readonly')

    _columns = {
        'value': fields.char('unknown', readonly=True)
    }

class char_states(orm.Model):
    _name = name('char.states')

    _columns = {
        'value': fields.char('unknown', readonly=True, states={'draft': [('readonly', False)]})
    }

class char_noreadonly(orm.Model):
    _name = name('char.noreadonly')

    _columns = {
        'value': fields.char('unknown', readonly=True, states={'draft': [('invisible', True)]})
    }

class char_stillreadonly(orm.Model):
    _name = name('char.stillreadonly')

    _columns = {
        'value': fields.char('unknown', readonly=True, states={'draft': [('readonly', True)]})
    }

# TODO: complex field (m2m, o2m, m2o)
class m2o(orm.Model):
    _name = name('m2o')

    _columns = {
        'value': fields.many2one(name('m2o.related'))
    }
class m2o_related(orm.Model):
    _name = name('m2o.related')

    _columns = {
        'value': fields.integer()
    }
    _defaults = {
        'value': 42
    }

class m2o_required(orm.Model):
    _name = name('m2o.required')

    _columns = {
        'value': fields.many2one(name('m2o.required.related'), required=True)
    }
class m2o_required_related(orm.Model):
    _name = name('m2o.required.related')

    _columns = {
        'value': fields.integer()
    }
    _defaults = {
        'value': 42
    }

class o2m(orm.Model):
    _name = name('o2m')

    _columns = {
        'value': fields.one2many(name('o2m.child'), 'parent_id')
    }
class o2m_child(orm.Model):
    _name = name('o2m.child')

    _columns = {
        'parent_id': fields.many2one(name('o2m')),
        'value': fields.integer()
    }

class preview_model(orm.Model):
    _name = name('preview')

    _columns = {
        'name': fields.char('Name'),
        'somevalue': fields.integer('Some Value', required=True),
        'othervalue': fields.integer('Other Variable'),
    }
