#
# test cases for model and scope
#

from datetime import date, datetime
from collections import defaultdict

from openerp import scope
from openerp.tests import common


class TestScope(common.TransactionCase):

    def test_00_model_access(self):
        """ test getting models from the scope object """
        model = scope.registry['res_partner']
        self.assertEqual(model._name, 'res_partner')
        model = scope['res_partner']
        self.assertEqual(model._name, 'res_partner')
        model = scope.res_partner
        self.assertEqual(model._name, 'res_partner')

        model = scope.registry['ir_model_access']
        self.assertEqual(model._name, 'ir_model_access')
        model = scope['ir_model_access']
        self.assertEqual(model._name, 'ir_model_access')
        model = scope.ir_model_access
        self.assertEqual(model._name, 'ir_model_access')

        with self.assertRaises(KeyError):
            model = scope.registry['foo_bar']
        with self.assertRaises(KeyError):
            model = scope['foo_bar']
        with self.assertRaises(KeyError):
            model = scope.foo_bar

    def test_10_model_inherit(self):
        """ test new-style model inheritance specification """
        instance = scope.test_new_api_foo.browse()
        self.assertEqual(instance.foo(), 'foobar')
