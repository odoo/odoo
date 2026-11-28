# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .test_common import TestHttpBase


class TestHttpNoDbQueryCount(TestHttpBase):
    def test_nodb_query_count_serve_static(self):
        with self.assertQueries([]):
            res = self.nodb_url_open('/base/static/description/icon.png')
        res.raise_for_status()
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers['Content-Disposition'], 'inline; filename=icon.png')

    def test_nodb_query_count_serve_nodb(self):
        with self.assertQueries([]):
            res = self.nodb_url_open('/web/login').raise_for_status()
        res.raise_for_status()
        self.assertEqual(res.status_code, 303)
        self.assertEqual(res.headers['Location'], '/web/database/selector')


class TestHttpQueryCount(TestHttpBase):
    def setUp(self):
        super().setUp()
        self.authenticate('demo', 'demo')

    def test_query_count_serve_static(self):
        with self.assertQueries([]):
            res = self.db_url_open('/base/static/description/icon.png')
        res.raise_for_status()
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers['Content-Disposition'], 'inline; filename=icon.png')

    def test_query_count_serve_nodb(self):
        with self.assertQueries([]):
            res = self.db_url_open('/web/login').raise_for_status()
        res.raise_for_status()
        self.assertEqual(res.status_code, 303)
        self.assertEqual(res.headers['Location'], '/web/database/selector')
