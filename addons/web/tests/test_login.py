# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import HttpCase, new_test_user

class TestWebLogin(HttpCase):
    def test_web_login(self):
        new_test_user(self.env, 'jackoneill', context={'lang': 'en_US'})

        # get login form
        res_get = self.url_open('/web/login')
        res_get.raise_for_status()
        csrf_anchor = '<input type="hidden" name="csrf_token" value="'
        csrf_token = res_get.text.partition(csrf_anchor)[2].partition('"')[0]

        # login
        res_post = self.url_open('/web/login', data={
            'login': 'jackoneill',
            'password': 'jackoneill',
            'csrf_token': csrf_token,
        })
        res_post.raise_for_status()

        # ensure we are logged-in
        self.url_open(
            '/web/session/check',
            headers={'Content-Type': 'application/json'},
            data='{}'
        ).raise_for_status()
