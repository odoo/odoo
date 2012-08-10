from openerp.tests.common import TransactionCase

ID_FIELD = {'id': 'id', 'name': 'id', 'string': "External ID", 'required': False, 'fields': []}
def make_field(name='value', string='unknown', required=False, fields=[]):
    return [
        ID_FIELD,
        {'id': name, 'name': name, 'string': string, 'required': required, 'fields': fields},
    ]

class test_basic_fields(TransactionCase):
    def get_fields(self, field):
        return self.registry('base_import.import')\
            .get_fields(self.cr, self.uid, 'base_import.tests.models.' + field)

    def test_base(self):
        """ A basic field is not required """
        self.assertEqual(self.get_fields('char'), make_field())

    def test_required(self):
        """ Required fields should be flagged (so they can be fill-required) """
        self.assertEqual(self.get_fields('char.required'), make_field(required=True))

    def test_readonly(self):
        """ Readonly fields should be filtered out"""
        self.assertEqual(self.get_fields('char.readonly'), [ID_FIELD])

    def test_readonly_states(self):
        """ Readonly fields with states should not be filtered out"""
        self.assertEqual(self.get_fields('char.states'), make_field())

    def test_readonly_states_noreadonly(self):
        """ Readonly fields with states having nothing to do with
        readonly should still be filtered out"""
        self.assertEqual(self.get_fields('char.noreadonly'), [ID_FIELD])

    def test_readonly_states_stillreadonly(self):
        """ Readonly fields with readonly states leaving them readonly
        always... filtered out"""
        self.assertEqual(self.get_fields('char.stillreadonly'), [ID_FIELD])

    def test_m2o(self):
        """ M2O fields should allow import of themselves (name_get),
        their id and their xid"""
        self.assertEqual(self.get_fields('m2o'), make_field(fields=[
            {'id': 'value', 'name': 'id', 'string': 'External ID', 'required': False, 'fields': []},
            {'id': 'value', 'name': '.id', 'string': 'Database ID', 'required': False, 'fields': []},
        ]))
    
    def test_m2o_required(self):
        """ If an m2o field is required, its three sub-fields are
        required as well (the client has to handle that: requiredness
        is id-based)
        """
        self.assertEqual(self.get_fields('m2o.required'), make_field(required=True, fields=[
            {'id': 'value', 'name': 'id', 'string': 'External ID', 'required': True, 'fields': []},
            {'id': 'value', 'name': '.id', 'string': 'Database ID', 'required': True, 'fields': []},
        ]))

class test_o2m(TransactionCase):
    def get_fields(self, field):
        return self.registry('base_import.import')\
            .get_fields(self.cr, self.uid, 'base_import.tests.models.' + field)

    def test_shallow(self):
        self.assertEqual(self.get_fields('o2m'), make_field(fields=[
            {'id': 'id', 'name': 'id', 'string': 'External ID', 'required': False, 'fields': []},
            # FIXME: should reverse field be ignored?
            {'id': 'parent_id', 'name': 'parent_id', 'string': 'unknown', 'required': False, 'fields': [
                {'id': 'parent_id', 'name': 'id', 'string': 'External ID', 'required': False, 'fields': []},
                {'id': 'parent_id', 'name': '.id', 'string': 'Database ID', 'required': False, 'fields': []},
            ]},
            {'id': 'value', 'name': 'value', 'string': 'unknown', 'required': False, 'fields': []},
        ]))
