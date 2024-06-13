
# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from uuid import uuid4
from odoo.tests.common import HttpCase, tagged, new_test_user


@tagged("-at_install", "post_install")
class TestOnboardingSession(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Delete all onboarding records
        onboarding_records = cls.env['onboarding.onboarding'].search([])
        onboarding_records.unlink()

        cls.user_password = "infooooo"
        cls.unauthorized_user = new_test_user(
            cls.env,
            "session",
            email="session@in.fo",
            password=cls.user_password,
            tz="UTC")

        cls.user = new_test_user(
            cls.env,
            "session2",
            email="session2@in.fo",
            password=cls.user_password,
            groups="base.group_system",
            tz="UTC")

        cls.payload = json.dumps(dict(jsonrpc="2.0", method="call", id=str(uuid4())))
        cls.headers = {
            "Content-Type": "application/json",
        }

    def test_session_no_onboarding(self):
        """ Checks that the session_info['onboarding_to_display'] is an empty list when no records"""
        self.authenticate(self.user.login, self.user_password)
        response = self.url_open("/web/session/get_session_info", data=self.payload, headers=self.headers)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        result = data["result"]
        self.assertEqual(result['onboarding_to_display'], [], "onboarding_to_display key in session\
            info should be an empty array")

    def test_session_onboarding(self):
        """ Checks that the session_info['onboarding_to_display'] correspond to the list of onboarding
        banner to display"""

        self.onboarding_closed = self.env['onboarding.onboarding'].create(
            {
                'name': 'Test Onboarding Closed',
                'route_name': 'onboarding_closed',
                'is_per_company': False,
                'is_onboarding_closed': True,
            })

        self.onboarding_open = self.env['onboarding.onboarding'].create(
            {
                'name': 'Test Onboarding Open',
                'route_name': 'onboarding_open',
                'is_per_company': False,
            })

        # create a fake action for step opening
        self.action_fake_open_onboarding_step = self.env['ir.actions.act_window'].create({
            'name': 'action_fake_open_onboarding_step',
            'res_model': 'onboarding.onboarding',
        })

        # Create and add steps
        self.onboarding_closed_step_1 = self.env['onboarding.onboarding.step'].create(
            {
                'title': 'Test Onboarding Closed - Step 1',
                'onboarding_ids': [self.onboarding_closed.id],
                'is_per_company': False,
                'panel_step_open_action_name': 'action_fake_open_onboarding_step',
            }
        )
        self.onboarding_open_step_1 = self.env['onboarding.onboarding.step'].create(
            {
                'title': 'Test Onboarding Open - Step 1',
                'onboarding_ids': [self.onboarding_open.id],
                'is_per_company': False,
                'panel_step_open_action_name': 'action_fake_open_onboarding_step',
            }
        )

        self.onboarding_closed.step_ids = [self.onboarding_closed_step_1.id]
        self.onboarding_open.step_ids = [self.onboarding_open_step_1.id]
        (self.onboarding_closed + self.onboarding_open)._search_or_create_progress()
        self.onboarding_closed.action_close()

        # Connect as group system user and verify the session
        self.authenticate(self.user.login, self.user_password)
        response = self.url_open("/web/session/get_session_info", data=self.payload, headers=self.headers)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        result = data["result"]
        self.assertEqual(result['onboarding_to_display'], ['onboarding_open'], "onboarding_to_display key in session\
            info should only contain onboarding_open")

        # Connect as unauthorized user and verify session
        self.authenticate(self.unauthorized_user.login, self.user_password)
        response = self.url_open("/web/session/get_session_info", data=self.payload, headers=self.headers)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        result = data["result"]

        self.assertIsNone(result.get('onboarding_to_display'), "onboarding_to_display key in session\
            info should be None when accessed by unauthorized user")
