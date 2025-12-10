# Part of Odoo. See LICENSE file for full copyright and licensing details.

from base64 import b64encode

from odoo import Command, tests
from odoo.tools import mute_logger
from odoo.tools.json import scriptsafe as json_safe

from odoo.addons.base.tests.common import HttpCaseWithUserDemo, HttpCaseWithUserPortal


@tests.tagged('-at_install', 'post_install')
class TestWebEditorController(HttpCaseWithUserDemo, HttpCaseWithUserPortal):

    def test_modify_image(self):
        gif_base64 = b"R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs="
        attachment = self.env['ir.attachment'].create({
            'name': 'test.gif',
            'mimetype': 'image/gif',
            'datas': gif_base64,
            'public': True,
            'res_model': 'ir.ui.view',
            'res_id': 0,
        })

        def modify(login, name, expect_fail=False):
            self.authenticate(login, login)
            svg = b'<svg viewBox="0 0 400 400"><!-- %s --><image url="data:image/gif;base64,%s" /></svg>' % (name.encode('ascii'), gif_base64)
            params = {
                'name': name,
                'mimetype': 'image/svg+xml',
                'data': b64encode(svg).decode('ascii'),
            }
            if attachment.res_id:
                params['res_model'] = attachment.res_model
                params['res_id'] = attachment.res_id
            response = self.url_open(
                f'/html_editor/modify_image/{attachment.id}',
                headers={'Content-Type': 'application/json'},
                data=json_safe.dumps({
                    "params": params,
                }),
            )
            self.assertEqual(200, response.status_code, "Expect response")
            if expect_fail:
                return json_safe.loads(response.content)
            url = json_safe.loads(response.content).get('result')
            self.assertTrue(url.endswith(name), "Expect name in URL")
            response = self.url_open(url)
            self.assertEqual(200, response.status_code, "Expect response")
            self.assertTrue('image/svg+xml' in response.headers.get('Content-Type'), "Expect SVG mimetype")
            self.assertEqual(svg, response.content, "Expect unchanged SVG")
            return True

        # Admin can modify page
        modify('admin', 'page-admin.gif')

        # Base user cannot modify page
        self.user_demo.write({
            'group_ids': [
                Command.clear(),
                Command.link(self.env.ref('base.group_user').id),
            ],
        })
        with mute_logger('odoo.http'):
            json = modify('demo', 'page-demofail.gif', True)
        self.assertFalse(json.get('result'), "Expect no URL when called with insufficient rights")

        # Restricted editor with event right cannot modify page
        self.user_demo.write({
            'group_ids': [
                Command.clear(),
                Command.link(self.env.ref('base.group_user').id),
                Command.link(self.env.ref('website.group_website_restricted_editor').id),
                Command.link(self.env.ref('event.group_event_manager').id),
            ],
        })
        with mute_logger('odoo.http'):
            json = modify('demo', 'page-demofail2.gif', True)
        self.assertFalse(json.get('result'), "Expect no URL when called with insufficient rights")

        # Website designer can modify page
        self.user_demo.write({
            'group_ids': [
                Command.clear(),
                Command.link(self.env.ref('base.group_user').id),
                Command.link(self.env.ref('website.group_website_designer').id),
            ],
        })
        modify('demo', 'page-demo.gif')

        event = self.env['event.event'].create({'name': 'test event'})
        attachment.res_model = 'event.event'
        attachment.res_id = event.id

        # Admin can modify event
        modify('admin', 'event-admin.gif')

        # Base user cannot modify event
        self.user_demo.write({
            'group_ids': [
                Command.clear(),
                Command.link(self.env.ref('base.group_user').id),
            ],
        })
        with mute_logger('odoo.http'):
            json = modify('demo', 'event-demofail.gif', True)
        self.assertFalse(json.get('result'), "Expect no URL when called with insufficient rights")

        # Restricted editor with sales rights cannot modify event
        self.user_demo.write({
            'group_ids': [
                Command.clear(),
                Command.link(self.env.ref('base.group_user').id),
                Command.link(self.env.ref('website.group_website_restricted_editor').id),
                Command.link(self.env.ref('sales_team.group_sale_manager').id),
            ],
        })
        with mute_logger('odoo.http'):
            json = modify('demo', 'event-demofail2.gif', True)
        self.assertFalse(json.get('result'), "Expect no URL when called with insufficient rights")

        # Restricted editor with event rights can modify event
        self.user_demo.write({
            'group_ids': [
                Command.clear(),
                Command.link(self.env.ref('base.group_user').id),
                Command.link(self.env.ref('website.group_website_restricted_editor').id),
                Command.link(self.env.ref('event.group_event_manager').id),
            ],
        })
        modify('demo', 'event-demo.gif')

        # Website designer cannot modify event
        self.user_demo.write({
            'group_ids': [
                Command.clear(),
                Command.link(self.env.ref('base.group_user').id),
                Command.link(self.env.ref('website.group_website_designer').id),
            ],
        })
        with mute_logger('odoo.http'):
            json = modify('demo', 'event-demofail3.gif', True)
        self.assertFalse(json.get('result'), "Expect no URL when called with insufficient rights")
