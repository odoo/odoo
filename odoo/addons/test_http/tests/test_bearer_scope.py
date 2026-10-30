# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime, timedelta
from http import HTTPStatus

from odoo.tests import tagged
from odoo.tools import mute_logger

from .test_common import TestHttpBase


@tagged('-at_install', 'post_install')
class TestBearerScope(TestHttpBase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        expiration = datetime.now() + timedelta(hours=12)
        cls.test_user = (user := cls.env.ref('base.test_user')).with_user(user)
        cls.rpc_key = cls.test_user.env['res.users.apikeys']._generate('rpc', 'test rpc key', expiration, readonly=False)
        cls.rpc_ro_key = cls.test_user.env['res.users.apikeys']._generate('rpc', 'test rpc key readonly', expiration, readonly=True)
        cls.other_key = cls.test_user.env['res.users.apikeys']._generate('other_scope', 'test other key', expiration, readonly=False)

    def test_rpc_key_works_on_rpc_endpoint(self):
        res = self.db_url_open('/test_http/greeting-bearer', headers={'Authorization': f'Bearer {self.rpc_key}'})
        self.assertEqual(res.status_code, HTTPStatus.OK)

    def test_rpc_key_rejected_on_non_rpc_endpoint(self):
        res = self.db_url_open('/test_http/greeting-bearer-other-scope', headers={'Authorization': f'Bearer {self.rpc_key}'})
        self.assertEqual(res.status_code, HTTPStatus.UNAUTHORIZED)

    def test_non_rpc_key_rejected_on_rpc_endpoint(self):
        res = self.db_url_open('/test_http/greeting-bearer', headers={'Authorization': f'Bearer {self.other_key}'})
        self.assertEqual(res.status_code, HTTPStatus.UNAUTHORIZED)

    def test_readonly_token(self):
        res = self.db_url_open('/test_http/greeting-bearer?readonly=1', headers={'Authorization': f'Bearer {self.rpc_ro_key}'})
        self.assertEqual(res.status_code, HTTPStatus.OK)

        milky_way = self.env.ref('test_http.milky_way')
        res = self.db_url_open('/json/2/test_http.galaxy/write',
            data=r'{"ids": [%s], "vals":{"name": "new name"}}' % milky_way.id,
            headers={
                'Authorization': f'Bearer {self.rpc_key}',  # read/write token
                'Content-Type': "application/json",
            },
        )
        self.assertEqual(res.status_code, HTTPStatus.OK)

        with mute_logger('odoo.http', 'odoo.sql_db'):
            res = self.db_url_open('/json/2/test_http.galaxy/write',
                data=r'{"ids": [%s], "vals":{"name": "new name"}}' % milky_way.id,
                headers={
                    'Authorization': f'Bearer {self.rpc_ro_key}',  # read-only token
                    'Content-Type': "application/json",
                },
            )
        self.assertNotEqual(res.status_code, HTTPStatus.OK)
