# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import datetime
import json

from unittest.mock import patch

from odoo.tools import mute_logger
from odoo.tests.common import HttpCase, tagged


class ProfilingHttpCase(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Trick: we patch db_connect() to make it return the registry; when the
        # profiler calls cursor() on it, it gets a test cursor (with cls.cr as
        # its actual cursor), which prevents the profiling data from being
        # committed for real.
        cls.patcher = patch('odoo.sql_db.db_connect', return_value=cls.registry)
        cls.startClassPatcher(cls.patcher)

    def profile_rpc(self, params=None):
        params = params or {}
        req = self.url_open(
            '/web/dataset/call_kw/ir.profile/set_profiling', # use model and method in route has web client does
            headers={'Content-Type': 'application/json'},
            data=json.dumps({'params':{
                'model': 'ir.profile',
                'method': 'set_profiling',
                'args': [],
                'kwargs': params,
            }})
        )
        req.raise_for_status()
        return req.json()

@tagged('post_install', '-at_install', 'profiling')
class TestProfilingWeb(ProfilingHttpCase):
    def test_profiling_enabled(self):
        # since profiling will use a direct connection to the database patch 'db_connect' to ensure we are using the test cursor
        self.authenticate('admin', 'admin')
        last_profile = self.env['ir.profile'].search([], limit=1, order='id desc')
        # Trying to start profiling when not enabled
        self.env['ir.config_parameter'].set_param('base.profiling_enabled_until', '')
        res = self.profile_rpc({'profile': 1})
        self.assertEqual(res['result']['res_model'], 'base.enable.profiling.wizard')
        self.assertEqual(last_profile, self.env['ir.profile'].search([], limit=1, order='id desc'))

        # Enable profiling and start blank profiling
        expiration = datetime.datetime.now() + datetime.timedelta(seconds=50)
        self.env['ir.config_parameter'].set_param('base.profiling_enabled_until', expiration)
        res = self.profile_rpc({'profile': 1})
        self.assertTrue(res['result']['session'])
        self.assertEqual(last_profile, self.env['ir.profile'].search([], limit=1, order='id desc'), "profiling route shouldn't have been profiled")
        # Profile a page
        res = self.url_open('/web/speedscope')  # profile a light route
        new_profile = self.env['ir.profile'].search([], limit=1, order='id desc')
        self.assertNotEqual(last_profile, new_profile, "A new profile should have been created")
        self.assertEqual(new_profile.name, '/web/speedscope?')

    def test_profile_test_tool(self):
        with self.profile():
            self.url_open('/web')

        descriptions = self.env['ir.profile'].search([], order='id desc', limit=3).mapped('name')
        self.assertEqual(descriptions, [
            f'test_profile_test_tool uid:{self.env.uid} warm ',
            f'test_profile_test_tool uid:{self.env.uid} warm /web/login?redirect=%2Fweb%3F',
            f'test_profile_test_tool uid:{self.env.uid} warm /web?',
        ])


@tagged('post_install', '-at_install', 'profiling')
class TestProfilingModes(ProfilingHttpCase):
    def test_profile_collectors(self):
        expiration = datetime.datetime.now() + datetime.timedelta(seconds=50)
        self.env['ir.config_parameter'].set_param('base.profiling_enabled_until', expiration)

        self.authenticate('admin', 'admin')
        res = self.profile_rpc({})
        self.assertEqual(res['result']['collectors'], None)
        res = self.profile_rpc({'profile': 1, 'collectors': ['sql', 'traces_async']})
        self.assertEqual(sorted(res['result']['collectors']), ['sql', 'traces_async'])
        res = self.profile_rpc({'collectors': ['sql']})
        self.assertEqual(res['result']['collectors'], ['sql'],)
        res = self.profile_rpc({'profile': 0})
        res = self.profile_rpc({'profile': 1})
        self.assertEqual(res['result']['collectors'], ['sql'],
                         "Enabling and disabling profiling shouldn't have change existing preferences")


@tagged('post_install', '-at_install', 'profiling')
class TestProfilingPublic(ProfilingHttpCase):

    def test_public_user_profiling(self):
        last_profile = self.env['ir.profile'].search([], limit=1, order='id desc')
        self.env['ir.config_parameter'].set_param('base.profiling_enabled_until', '')
        self.authenticate(None, None)

        res = self.url_open('/web/set_profiling?profile=1')
        self.assertEqual(res.status_code, 500)
        self.assertEqual(res.text, 'error: Profiling is not enabled on this database. Please contact an administrator.')

        expiration = datetime.datetime.now() + datetime.timedelta(seconds=50)
        self.env['ir.config_parameter'].set_param('base.profiling_enabled_until', expiration)
        res = self.url_open('/web/set_profiling?profile=1')
        self.assertEqual(res.status_code, 200)
        res = res.json()
        self.assertTrue(res.pop('session'))
        self.assertEqual(res, {"collectors": ["sql", "traces_async"], "params": {}})
        self.assertEqual(last_profile, self.env['ir.profile'].search([], limit=1, order='id desc'), "profiling route shouldn't have been profiled")

        res = self.url_open('/web/login')  # profile /web/login to avoid redirections of /
        new_profile = self.env['ir.profile'].search([], limit=1, order='id desc')
        self.assertNotEqual(last_profile, new_profile, "A route should have been profiled")
        self.assertEqual(new_profile.name, '/web/login?')
