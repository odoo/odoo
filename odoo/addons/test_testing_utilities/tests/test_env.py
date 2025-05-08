from odoo import Command
from odoo.tests.common import TransactionCase


class TestEnv(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        user = cls.env['res.users'].create({
            'name': 'superuser',
            'login': 'superuser',
            'group_ids': [Command.set(cls.env.user.group_ids.ids)],
        })

        # We need at least two different environments in the current transaction.
        cls.env = cls.env(user=user)
        cls.sudo_env = cls.env(su=True)

    def test_env_lazy_properties_cleanup_between_tests_part_01(self):
        """
        Set up for test_env_cleanup_between_tests_part_02`.
        Add a lazy property (company) to the environments.
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

    def test_env_lazy_properties_cleanup_between_tests_part_02(self):
        """
        Follow up of test_env_lazy_properties_cleanup_between_tests_part_01.
        Test that the lazy property (company) was cleared from the environments.
        """
        self.assertEqual(self.env.company, self.env.user.company_id)
        self.assertTrue(self.env.company.exists())

        self.assertEqual(self.sudo_env.company, self.env.user.company_id)
        self.assertTrue(self.sudo_env.company.exists())
