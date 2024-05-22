# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import TransactionCase


class TestResConfigSettingsFields(TransactionCase):
    def test_config_parameter_default_truthy(self):
        settings = self.env['res.config.settings'].create({})
        self.assertTrue(settings.test_bool)
        self.assertEqual(settings.test_int, 30)
        self.assertTrue(settings.test_float > 0.1)

        settings.write({
            'test_bool': False,
            'test_int': 0,
            'test_float': 0.000,
        })
        settings.set_values()

        settings = self.env['res.config.settings'].create({})
        self.assertFalse(settings.test_bool)
        self.assertEqual(settings.test_int, 0)
        self.assertTrue(settings.test_float < 0.1)

        settings.write({
            'test_bool': True,
            'test_int': 1,
            'test_float': 3.0,
        })
        settings.set_values()

        settings = self.env['res.config.settings'].create({})
        self.assertTrue(settings.test_bool)
        self.assertEqual(settings.test_int, 1)
        self.assertTrue(settings.test_float > 2.0)
