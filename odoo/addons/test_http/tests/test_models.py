# Part of Odoo. See LICENSE file for full copyright and licensing details.

import html
from odoo.tests import tagged
from odoo.tests.common import new_test_user
from odoo.tools import mute_logger
from odoo.addons.test_http.utils import HtmlTokenizer

from .test_common import TestHttpBase


@tagged('post_install', '-at_install')
class TestHttpModels(TestHttpBase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.jackoneill = new_test_user(cls.env, 'jackoneill', context={'lang': 'en_US'})

    def setUp(self):
        super().setUp()
        self.authenticate('jackoneill', 'jackoneill')

    def test_models0_galaxy_ok(self):
        milky_way = self.env.ref('test_http.milky_way')

        res = self.url_open(f"/test_http/{milky_way.id}")

        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            HtmlTokenizer.tokenize(res.text),
            HtmlTokenizer.tokenize('''\
                <p>Milky Way</p>
                <ul>
                    <li><a href="/test_http/1/1">Earth (P4X-126)</a></li>
                    <li><a href="/test_http/1/2">Abydos (P2X-125)</a></li>
                    <li><a href="/test_http/1/3">Dakara (P5C-113)</a></li>
                </ul>
                ''')
            )

    @mute_logger('odoo.http')
    def test_models1_galaxy_ko(self):
        res = self.url_open("/test_http/404")  # unknown galaxy
        self.assertEqual(res.status_code, 400)
        self.assertIn('The Ancients did not settle there.', res.text)

    def test_models2_stargate_ok(self):
        milky_way = self.env.ref('test_http.milky_way')
        earth = self.env.ref('test_http.earth')

        res = self.url_open(f'/test_http/{milky_way.id}/{earth.id}')

        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            HtmlTokenizer.tokenize(res.text),
            HtmlTokenizer.tokenize('''\
                <dl>
                    <dt>name</dt><dd>Earth</dd>
                    <dt>address</dt><dd>sq5Abt</dd>
                    <dt>sgc_designation</dt><dd>P4X-126</dd>
                </dl>
            ''')
        )

    @mute_logger('odoo.http')
    def test_models3_stargate_ko(self):
        milky_way = self.env.ref('test_http.milky_way')
        res = self.url_open(f'/test_http/{milky_way.id}/9999')  # unknown gate
        self.assertEqual(res.status_code, 400)
        self.assertIn("The goa'uld destroyed the gate", html.unescape(res.text))
