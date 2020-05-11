from functools import partial
from json import dumps
from pprint import pformat
from sys import version_info
from xmlrpc.client import ServerProxy

from odoo.tests import get_db_name, HttpCase, tagged
from odoo.tools import config

HOST = '127.0.0.1'
PORT = config['http_port']


class TestAllowNone(HttpCase):
    def setUp(self):
        super(TestAllowNone, self).setUp()
        self.db = get_db_name()
        self.domain = [
            ('active', '=', False),
            ('date', '=', False),
            ('parent_id', '=', False),
        ]
        self.pw = 'admin'
        self.uid = self.ref('base.user_admin')
        self.xmlrpc = partial(self.xmlrpc_object.execute_kw, self.db, self.uid, self.pw)

    def jsonrpc(self, *args, url='/jsonrpc'):
        data = {
            'jsonrpc': '2.0',
            'method': 'call',
            'params': {
                'service': 'object',
                'method': 'execute_kw',
                'args': [self.db, self.uid, self.pw, *args],
            }
        }
        headers = {'content-type': 'application/json'}
        return self.url_open(url, data=dumps(data), headers=headers).json()['result']

    def jsonrpc_2(self, *args):
        return self.jsonrpc(*args, url='/jsonrpc/2')

    def test_json_accept_null(self):
        partner = self.jsonrpc_2('res.partner', 'search_read', [], {
            'domain': self.domain,
            'limit': 1,
        })[0]
        self.assertIs(partner['active'], False, 'Boolean must be False')
        self.assertIs(partner['date'], None, 'Date must be None when when allow_none is set')
        self.assertIs(partner['parent_id'], None, 'Many2one must be None when when allow_none is set')

    def test_json_reject_null(self):
        partner = self.jsonrpc('res.partner', 'search_read', [], {
            'domain': self.domain,
            'limit': 1,
        })[0]
        self.assertIs(partner['active'], False, 'Boolean must be False')
        self.assertIs(partner['date'], False, 'Date must be False when allow_none is unset')
        self.assertIs(partner['parent_id'], False, 'Many2one must be False when allow_none is unset')

    def test_xml_accept_nil(self):
        if version_info < (3, 8):
            self.skipTest("xmlrpc.client.ServerProxy headers kwarg not available")

        xmlrpc_object = ServerProxy('http://%s:%d/xmlrpc/2/' % (HOST, PORT), headers={'XML-RPC-Accept-Nil': '1'})
        xmlrpc = partial(xmlrpc_object.execute_kw, self.db, self.uid, self.pw)
        partner = xmlrpc('res.partner', 'search_read', [], {
            'domain': self.domain,
            'limit': 1,
        })[0]
        self.assertIs(partner['active'], False, 'Boolean must be False')
        self.assertIs(partner['date'], None, 'Date must be None when when allow_none is set')
        self.assertIs(partner['parent_id'], None, 'Many2one must be None when allow_none is set')

    def test_xml_reject_nil(self):
        partner = self.xmlrpc('res.partner', 'search_read', [], {
            'domain': self.domain,
            'limit': 1,
        })[0]
        self.assertIs(partner['active'], False, 'Boolean must be False')
        self.assertIs(partner['date'], False, 'Date must be False when allow_none is unset')
        self.assertIs(partner['parent_id'], False, 'Many2one must be False when allow_none is unset')
