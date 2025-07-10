# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime, timedelta
from http import HTTPStatus

from odoo.tests import Like, get_db_name, new_test_user, tagged

from .test_common import TestHttpBase
from odoo.addons.test_http.controllers import CT_JSON

SEC_FETCH_HEADERS = {
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
}


@tagged('-at_install', 'post_install')
class TestHttpWebJson_2(TestHttpBase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.jackoneill = new_test_user(cls.env, 'jackoneill', context={'lang': 'en_US'})
        cls.jackoneill = cls.jackoneill.with_user(cls.jackoneill)
        key = cls.jackoneill.env['res.users.apikeys']._generate(
            scope='rpc', name='test', expiration_date=datetime.now() + timedelta(days=0.5))
        cls.bearer_header = {"Authorization": f"Bearer {key}"}

    def test_webjson2_multi_db_no_header(self):
        res = self.multidb_url_open(
            '/json/2/res.users/search',
            data=r'{"domain": []}',
            headers=CT_JSON | self.bearer_header,
            dblist=(get_db_name(), 'another-database'),
        )
        self.assertIn("The requested URL was not found on the server.", res.text)
        self.assertEqual(res.status_code, HTTPStatus.NOT_FOUND)
        self.assertEqual(res.headers.get('Content-Type'), 'text/html; charset=utf-8')

    def test_webjson2_multi_db_bad_header(self):
        res = self.multidb_url_open(
            '/json/2/res.users/search',
            data=r'{"domain": []}',
            headers={**CT_JSON, **self.bearer_header,
                'X-odoo-database': f'{get_db_name()}-idontexist',
            },
            dblist=(get_db_name(), 'another-database'),
        )
        self.assertIn("The requested URL was not found on the server.", res.text)
        self.assertEqual(res.status_code, HTTPStatus.NOT_FOUND)
        self.assertEqual(res.headers.get('Content-Type'), 'text/html; charset=utf-8')

    def test_webjson2_multi_db_good_header(self):
        res = self.multidb_url_open(
            '/json/2/res.users/read',
            data=r'{}',
            headers={**CT_JSON, **self.bearer_header,
                'X-odoo-database': get_db_name(),
            },
            dblist=(get_db_name(), 'another-database'),
        )
        self.assertEqual(res.text, "[]")
        self.assertEqual(res.status_code, HTTPStatus.OK)
        self.assertEqual(res.headers.get('Content-Type'), 'application/json; charset=utf-8')

    def test_webjson2_bad_content_type(self):
        res = self.db_url_open(
            # application/x-www-form-urlencoded
            '/json/2/res.users/search',
            data={"domain": []},
            headers=self.bearer_header,
        )
        self.assertEqual(res.text, Like("""
            ...Request inferred type is compatible with...http...but...
            /json/2...is type=...json...
        """))
        self.assertEqual(res.status_code, HTTPStatus.UNSUPPORTED_MEDIA_TYPE)
        self.assertEqual(res.headers.get('Content-Type'), 'text/html; charset=utf-8')

    def test_webjson2_bad_data(self):
        res = self.db_url_open(
            '/json/2/res.users/search',
            data=r"not json",
            headers=CT_JSON | self.bearer_header,
        )
        self.assertEqual(res.text, '"could not parse the body as json: Expecting value: line 1 column 1 (char 0)"')
        self.assertEqual(res.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(res.headers.get('Content-Type'), 'application/json; charset=utf-8')

    def test_webjson2_not_json_object(self):
        res = self.db_url_open(
            '/json/2/res.users/search',
            data=r'null',
            headers=CT_JSON | self.bearer_header,
        )
        self.assertEqual(res.text, '''"could not parse the body, expecting a json object"''')
        self.assertEqual(res.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(res.headers.get('Content-Type'), 'application/json; charset=utf-8')

    def test_webjson2_missing_auth(self):
        res = self.db_url_open(
            '/json/2/res.users/search',
            data=r'{"domain": []}',
            headers=CT_JSON,
        )
        self.assertEqual(res.status_code, HTTPStatus.UNAUTHORIZED)

    def test_webjson2_missing_argument(self):
        res = self.db_url_open(
            '/json/2/res.users/search',
            data=r'{}',
            headers=CT_JSON | self.bearer_header,
        )
        self.assertEqual(res.text, '''"missing a required argument: 'domain'"''')
        self.assertEqual(res.status_code, HTTPStatus.UNPROCESSABLE_ENTITY)
        self.assertEqual(res.headers.get('Content-Type'), 'application/json; charset=utf-8')

    def test_webjson2_good(self):
        res = self.db_url_open(
            '/json/2/res.users/search',
            data=r'{"domain": [["id","=",%d]]}' % self.jackoneill.id,
            headers=CT_JSON | self.bearer_header,
        )
        self.assertEqual(res.text, f"[{self.jackoneill.id}]")
        self.assertEqual(res.status_code, HTTPStatus.OK)
        self.assertEqual(res.headers.get('Content-Type'), 'application/json; charset=utf-8')

    def test_webjson2_api_model(self):
        res = self.db_url_open(
            '/json/2/res.users/create',
            data=r'{"ids": [0]}',
            headers=CT_JSON | self.bearer_header,
        )
        self.assertEqual(res.text, '''"cannot call res.users.create with ids"''')
        self.assertEqual(res.status_code, HTTPStatus.UNPROCESSABLE_ENTITY)
        self.assertEqual(res.headers.get('Content-Type'), 'application/json; charset=utf-8')
