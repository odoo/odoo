# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
from uuid import uuid4

from odoo import Command
from odoo.tests import common


class TestSessionInfo(common.HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env['res.company'].create({'name': "A"})
        cls.company_b = cls.env['res.company'].create({'name': "B"})
        cls.company_c = cls.env['res.company'].create({'name': "C"})
        cls.company_b_branch = cls.env['res.company'].create({'name': "B Branch", 'parent_id': cls.company_b.id})
        cls.allowed_companies = cls.company_a + cls.company_b_branch + cls.company_c
        cls.disallowed_ancestor_companies = cls.company_b

        cls.user_password = "info"
        cls.user = common.new_test_user(
            cls.env,
            "session",
            email="session@in.fo",
            password=cls.user_password,
            tz="UTC")
        cls.user.write({
            'company_id': cls.company_a.id,
            'company_ids': [Command.set(cls.allowed_companies.ids)],
        })

        cls.payload = json.dumps(dict(jsonrpc="2.0", method="call", id=str(uuid4())))
        cls.headers = {
            "Content-Type": "application/json",
        }

    def test_session_info(self):
        """ Checks that the session_info['user_companies'] structure correspond to what is expected """
        self.authenticate(self.user.login, self.user_password)
        response = self.url_open("/web/session/get_session_info", data=self.payload, headers=self.headers)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        result = data["result"]

        expected_allowed_companies = {
            str(company.id): {
                'id': company.id,
                'name': company.name,
                'sequence': company.sequence,
                'child_ids': company.child_ids.ids,
                'parent_id': company.parent_id.id,
            } for company in self.allowed_companies
        }

        expected_disallowed_ancestor_companies = {
            str(company.id): {
                'id': company.id,
                'name': company.name,
                'sequence': company.sequence,
                'child_ids': company.child_ids.ids,
                'parent_id': company.parent_id.id,
            } for company in self.disallowed_ancestor_companies
        }

        expected_user_companies = {
            'current_company': self.company_a.id,
            'allowed_companies': expected_allowed_companies,
            'disallowed_ancestor_companies': expected_disallowed_ancestor_companies,
        }
        self.assertEqual(
            result['user_companies'],
            expected_user_companies,
            "The session_info['user_companies'] does not have the expected structure")

    def test_session_modules(self):
        self.authenticate(self.user.login, self.user_password)
        response = self.url_open("/web/session/modules", data=self.payload, headers=self.headers)
        data = response.json()
        self.assertTrue(isinstance(data['result'], list))
