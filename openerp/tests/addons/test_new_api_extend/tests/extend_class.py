from openerp.tests import common
import openerp.tools


class TestClassChanges(common.TransactionCase):
    """ Test model inheritance/alterations
    """
    def setUp(self):
        super(TestClassChanges, self).setUp()
        self.Model = self.registry('test_new_api.defaults')

    def test_create_with_defaults(self):
        id = self.Model.create({})
        record = self.Model.browse(id)

        self.assertEqual(record.name, u"Bob the Builder")
        self.assertEqual(record.description, u"This is a thing")

    @openerp.tools.mute_logger('openerp.sql_db')
    def test_create_with_empty_name(self):
        with self.assertRaises(Exception):
            self.Model.create({'name': False})

    @openerp.tools.mute_logger('openerp.sql_db')
    def test_create_with_empty_description(self):
        with self.assertRaises(Exception):
            self.Model.create({'description': False})
