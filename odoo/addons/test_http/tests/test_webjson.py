# Part of Odoo. See LICENSE file for full copyright and licensing details.
import html
from base64 import b64encode
from odoo.fields import Command
from odoo.tests import tagged
from odoo.tools import file_open
from .test_common import TestHttpBase

CT_HTML = 'text/html; charset=utf-8'


@tagged('-at_install', 'post_install')
class TestHttpWebJson_18_0(TestHttpBase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.milky_way = cls.env.ref('test_http.milky_way')
        cls.earth = cls.env.ref('test_http.earth')
        with file_open('test_http/static/src/img/gizeh.png', 'rb') as file:
            cls.gizeh_data = file.read()
            cls.gizeh_b64 = b64encode(cls.gizeh_data).decode()

    def test_webjson_access_error(self):
        self.authenticate('demo', 'demo')
        with self.assertLogs('odoo.http', 'WARNING') as capture:
            res = self.url_open('/json/18.0/settings')
            self.assertEqual(res.status_code, 403)
            self.assertEqual(res.headers['Content-Type'], 'text/html; charset=utf-8')
        self.assertIn("You are not allowed to access", res.text)
        self.assertEqual(len(capture.output), 1)
        self.assertIn("You are not allowed to access", capture.output[0])

    def test_webjson_access_error_crm(self):
        action_crm = self.env['ir.actions.server'].search([('path', '=', 'crm')])
        if not action_crm:
            self.skipTest("crm is not installed")

        self.authenticate('demo', 'demo')
        self.url_open('/json/18.0/crm').raise_for_status()

        self.env['ir.model.access'].search([
            ('model_id', '=', action_crm.model_id.id)
        ]).perm_read = False

        with self.assertLogs('odoo.http', 'WARNING') as capture:
            res = self.url_open('/json/18.0/crm')
            self.assertEqual(res.status_code, 403)
            self.assertEqual(res.headers['Content-Type'], 'text/html; charset=utf-8')
        self.assertIn("You are not allowed to access", res.text)
        self.assertEqual(len(capture.output), 1)
        self.assertIn("You are not allowed to access", capture.output[0])

    def test_webjson_access_export(self):
        # a simple call
        url = f'/json/18.0/test_http.stargate/{self.earth.id}'
        self.authenticate('demo', 'demo')
        res = self.url_open(url)
        res.raise_for_status()

        # remove export permssion
        group_export = self.env.ref('base.group_allow_export')
        self.user_demo.write({'groups_id': [Command.unlink(group_export.id)]})

        # check that demo has no access to /json
        with self.assertLogs('odoo.http', 'WARNING') as capture:
            res = self.url_open(url)
            self.assertIn("need export permissions", res.text)
            self.assertEqual(res.status_code, 403)
            self.assertIn("need export permissions", capture.output[0])

    def test_webjson_bad_stuff(self):
        self.authenticate('demo', 'demo')

        with self.subTest(bad='action'):
            res = self.url_open('/json/18.0/idontexist')
            self.assertEqual(res.status_code, 400)
            self.assertEqual(res.headers['Content-Type'], CT_HTML)
            self.assertIn(
                "expected action at word 1 but found “idontexist”", res.text)

        with self.subTest(bad='active_id'):
            res = self.url_open('/json/18.0/5/test_http.stargate')
            self.assertEqual(res.status_code, 400)
            self.assertEqual(res.headers['Content-Type'], CT_HTML)
            self.assertIn("expected action at word 1 but found “5”", res.text)

        with self.subTest(bad='record_id'):
            res = self.url_open('/json/18.0/test_http.stargate/1/2')
            self.assertEqual(res.status_code, 400)
            self.assertEqual(res.headers['Content-Type'], CT_HTML)
            self.assertIn("expected action at word 3 but found “2”", res.text)

        with self.subTest(bad='view_type'):
            error = "No default view of type 'idontexist' could be found!"
            with self.assertLogs('odoo.http', 'WARNING') as capture:
                res = self.url_open('/json/18.0/res.users?view_type=idontexist')
                self.assertEqual(res.status_code, 400)
                self.assertEqual(res.headers['Content-Type'], CT_HTML)
                self.assertIn(error, html.unescape(res.text))
            self.assertEqual(capture.output, [f"WARNING:odoo.http:{error}"])

    def test_webjson_form(self):
        self.authenticate('demo', 'demo')
        res = self.url_open(f'/json/18.0/test_http.stargate/{self.earth.id}')
        res.raise_for_status()
        self.assertEqual(res.json(), {
            'id': self.earth.id,
            'name': self.earth.name,
            'sgc_designation': self.earth.sgc_designation,
            'galaxy_id': {'id': self.earth.galaxy_id.id,
                          'display_name': self.earth.galaxy_id.name},
            'glyph_attach': self.gizeh_b64,
            'glyph_inline': self.gizeh_b64,
        })

    def test_webjson_form_subtree(self):
        self.authenticate('demo', 'demo')
        res = self.url_open(f'/json/18.0/test_http.galaxy/{self.milky_way.id}')
        res.raise_for_status()
        self.assertEqual(
            res.json(),
            self.milky_way.web_read({
                'name': {},
                'stargate_ids': {'fields': {
                    'name': {},
                    'sgc_designation': {}
                }},
            })[0],
        )

    def test_webjson_form_viewtype_list(self):
        self.authenticate('demo', 'demo')
        url = f'/json/18.0/test_http.stargate/{self.earth.id}'
        res = self.url_open(f'{url}?view_type=list')
        res.raise_for_status()
        self.assertEqual(res.json(), {
            'id': self.earth.id,
            'name': self.earth.name,
            'sgc_designation': self.earth.sgc_designation,
        })

    def test_webjson_tree(self):
        self.authenticate('demo', 'demo')
        res = self.url_open('/json/18.0/test_http.stargate')
        res.raise_for_status()
        self.assertEqual(
            res.json(),
            self.env['test_http.stargate']
                .web_search_read([], {'name': {}, 'sgc_designation': {}})
        )

    def test_webjson_tree_limit_offset(self):
        self.authenticate('demo', 'demo')
        url = '/json/18.0/test_http.stargate'
        stargates = (
            self.env['test_http.stargate']
                .web_search_read([], {'name': {}, 'sgc_designation': {}})
        )['records']

        res_limit = self.url_open(f'{url}?limit=1')
        res_limit.raise_for_status()
        self.assertEqual(res_limit.json(), {
            'length': len(stargates),
            'records': stargates[:1]
        })

        res_offset = self.url_open(f'{url}?offset=1')
        res_offset.raise_for_status()
        self.assertEqual(res_offset.json(), {
            'length': len(stargates),
            'records': stargates[1:]
        })

        res_limit_offset = self.url_open(f'{url}?limit=1&offset=1')
        res_limit_offset.raise_for_status()
        self.assertEqual(res_limit_offset.json(), {
            'length': len(stargates),
            'records': stargates[1:2]
        })
