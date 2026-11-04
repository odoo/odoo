# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestEnv(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestEnv, cls).setUpClass()
        user = cls.env['res.users'].create({
            'name': 'superuser',
            'login': 'superuser',
            'password': 'superuser',
            'groups_id': [(6, 0, cls.env.user.groups_id.ids)],
        })
        cls.env = cls.env(user=user)

        # make sure there is at least another environment in the current transaction
        cls.sudo_env = cls.env(su=True)

    def test_env_company_part_01(self):
        """
        The main goal of the test is actually to check the values of the
        environment after this test execution (see test_env_company_part_02)
        """
        company = self.env['res.company'].create({
            "name": "Test Company",
        })
        self.env.user.write({
            'company_id': company.id,
            'company_ids': [(4, company.id), (4, self.env.company.id)],
        })
        self.assertEqual(self.env.company, self.env.user.company_id)
        self.assertTrue(self.env.company.exists())
        self.assertEqual(self.sudo_env.company, self.env.user.company_id)
        self.assertTrue(self.sudo_env.company.exists())

    def test_env_company_part_02(self):
        self.assertEqual(self.env.company, self.env.user.company_id)
        self.assertTrue(self.env.company.exists())
        self.assertEqual(self.sudo_env.company, self.env.user.company_id)
        self.assertTrue(self.sudo_env.company.exists())
