from http import HTTPStatus

import odoo.tools
from odoo.tests import HttpCase, HOST


class TestCustomAuth(HttpCase):
    # suppress "WARNING: Access Error" when auth fails on json endpoints
    @odoo.tools.mute_logger('odoo.http')
    def test_json(self):
        # straight request should fail
        r = self.url_open('/test_auth_custom/json', headers={'Content-Type': 'application/json'}, data="{}")
        e = r.json()['error']
        self.assertEqual(e['data']['name'], 'odoo.exceptions.AccessDenied')

        # but preflight should work
        self.env.flush_all()
        url = f"{self.base_url()}/test_auth_custom/json"
        r = self.url_open(url, method='OPTIONS', headers={
            'Origin': 'localhost',
            'Access-Control-Request-Method': 'QUX',
            'Access-Control-Request-Headers': 'XYZ',
        })
        self.assertTrue(r.ok)
        self.assertEqual(r.headers['Access-Control-Allow-Origin'], '*')
        self.assertEqual(r.headers['Access-Control-Allow-Methods'], 'POST', "json is always POST")
        self.assertNotIn('XYZ', r.headers['Access-Control-Allow-Headers'], "headers are ignored")

    @odoo.tools.mute_logger('odoo.http')
    def test_http(self):
        # straight request should fail
        r = self.url_open('/test_auth_custom/http')
        self.assertEqual(r.status_code, HTTPStatus.FORBIDDEN)

        # but preflight should work
        self.env.flush_all()
        url = f"{self.base_url()}/test_auth_custom/http"
        r = self.url_open(url, method='OPTIONS', headers={
            'Origin': 'localhost',
            'Access-Control-Request-Method': 'QUX',
            'Access-Control-Request-Headers': 'XYZ',
        })
        self.assertTrue(r.ok, r.text)
        self.assertEqual(r.headers['Access-Control-Allow-Origin'], '*')
        self.assertEqual(r.headers['Access-Control-Allow-Methods'], 'GET, OPTIONS',
                         "http is whatever's on the endpoint")
        self.assertNotIn('XYZ', r.headers['Access-Control-Allow-Headers'], "headers are ignored")
