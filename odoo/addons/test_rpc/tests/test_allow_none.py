from functools import partial
from json import dumps
from pprint import pformat

from odoo.tests import common, tagged
from odoo.tools.misc import mute_logger


class TestAllowNone(common.HttpCase):
    def setUp(self):
        super(TestAllowNone, self).setUp()
        self.db = common.get_db_name()
        self.domain = [
            ('active', '=', False),
            ('date', '=', False),
            ('parent_id', '=', False),
        ]
        self.pw = 'admin'
        self.uid = self.ref('base.user_admin')
        self.xmlrpc = partial(self.xmlrpc_object.execute_kw, self.db, self.uid, self.pw)

    def jsonrpc(self, *args):
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
        return self.url_open('/jsonrpc', data=dumps(data), headers=headers).json()['result']

    def test_json_allow_none_set(self):
        partner = self.jsonrpc('res.partner', 'search_read', [], {
            'context': {'allow_none': True},
            'domain': self.domain,
            'limit': 1,
        })[0]
        self.assertIs(partner['active'], False, 'Boolean must be False')
        self.assertIs(partner['date'], None, 'Date must be None when when allow_none is set')
        self.assertIs(partner['parent_id'], None, 'Many2one must be None when when allow_none is set')

    def test_json_allow_none_unset(self):
        partner = self.jsonrpc('res.partner', 'search_read', [], {
            'domain': self.domain,
            'limit': 1,
        })[0]
        self.assertIs(partner['active'], False, 'Boolean must be False')
        self.assertIs(partner['date'], False, 'Date must be False when allow_none is unset')
        self.assertIs(partner['parent_id'], False, 'Many2one must be False when allow_none is unset')

    def test_xml_allow_none_set(self):
        partner = self.xmlrpc('res.partner', 'search_read', [], {
            'context': {'allow_none': True},
            'domain': self.domain,
            'limit': 1,
        })[0]
        self.assertIs(partner['active'], False, 'Boolean must be False')
        self.assertIs(partner['date'], None, 'Date must be None when when allow_none is set')
        self.assertIs(partner['parent_id'], None, 'Many2one must be None when allow_none is set')

    def test_xml_allow_none_unset(self):
        partner = self.xmlrpc('res.partner', 'search_read', [], {
            'domain': self.domain,
            'limit': 1,
        })[0]
        self.assertIs(partner['active'], False, 'Boolean must be False')
        self.assertIs(partner['date'], False, 'Date must be False when allow_none is unset')
        self.assertIs(partner['parent_id'], False, 'Many2one must be False when allow_none is unset')
