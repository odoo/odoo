from openerp.osv import orm, fields

class TestObject(orm.Model):
    _name = 'web_tests_demo.model'

    _columns = {
        'name': fields.char("Name", required=True),
        'thing': fields.char("Thing"),
        'other': fields.char("Other", required=True)
    }
    _defaults = {
        'other': "bob"
    }

