# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common


@common.tagged('post_install', '-at_install')
class TestXMLRPC(common.HttpCase):

    def setUp(self):
        super(TestXMLRPC, self).setUp()
        self.admin_uid = self.env.ref('base.user_admin').id

    def test_01_xmlrpc_login(self):
        """ Try to login on the common service. """
        db_name = common.get_db_name()
        uid = self.xmlrpc_common.login(db_name, 'admin', 'admin')
        self.assertEqual(uid, self.admin_uid)

    def test_xmlrpc_ir_model_search(self):
        """ Try a search on the object service. """
        o = self.xmlrpc_object
        db_name = common.get_db_name()
        ids = o.execute(db_name, self.admin_uid, 'admin', 'ir.model', 'search', [])
        self.assertIsInstance(ids, list)
        ids = o.execute(db_name, self.admin_uid, 'admin', 'ir.model', 'search', [], {})
        self.assertIsInstance(ids, list)

    def test_xmlrpc_read_group(self):
        groups = self.xmlrpc_object.execute(
            common.get_db_name(), self.admin_uid, 'admin',
            'res.partner', 'read_group', [], ['is_company', 'color'], ['parent_id']
        )

    def test_xmlrpc_name_search(self):
        self.xmlrpc_object.execute(
            common.get_db_name(), self.admin_uid, 'admin',
            'res.partner', 'name_search', "admin"
        )

    def test_jsonrpc_read_group(self):
        self._json_call(
            common.get_db_name(), self.admin_uid, 'admin',
            'res.partner', 'read_group', [], ['is_company', 'color'], ['parent_id']
        )

    def test_jsonrpc_name_search(self):
        # well that's some sexy sexy call right there
        self._json_call(
            common.get_db_name(),
            self.admin_uid, 'admin',
            'res.partner', 'name_search', 'admin'
        )

    def _json_call(self, *args):
        self.opener.post("http://%s:%s/jsonrpc" % (common.HOST, common.PORT), json={
            'jsonrpc': '2.0',
            'id': None,
            'method': 'call',
            'params': {
                'service': 'object',
                'method': 'execute',
                'args': args
            }
        })
