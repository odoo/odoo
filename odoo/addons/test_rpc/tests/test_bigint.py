from functools import partial

from odoo.tests import HttpCase, get_db_name, tagged


@tagged('-at_install', 'post_install')
class TestXmlRpcBigInt(HttpCase):

    def setUp(self):
        super().setUp()
        uid = self.ref('base.user_admin')
        self.rpc = partial(self.xmlrpc_object.execute, get_db_name(), uid, 'admin')

    def test_xmlrpc_int8(self):
        self.assertEqual(self.env['test_rpc.model_a'].int8(), 1 << 32)
        int8 = self.rpc('test_rpc.model_a', 'int8')
        self.assertEqual(int8, 1 << 32)

    def test_xmlrpc_bigint(self):
        self.assertEqual(self.env['test_rpc.model_a'].bigint(), 1 << 64)
        bigint = self.rpc('test_rpc.model_a', 'bigint')
        self.assertEqual(bigint, 1 << 64)
