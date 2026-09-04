# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from unittest.mock import patch
from odoo.tests.common import TransactionCase

class TestResConfig(TransactionCase):

    def test_00_add_parameter_with_default_value(self):
        """ Check if parameters with a default value are saved in the ir_config_parameter table """

        self.env['res.config.test'].create({}).execute()
        self.assertEqual(self.env['ir.config_parameter'].sudo().get_param('resConfigTest.parameter1'), str(1000),
            "The parameter is not saved with its default value")

        with patch('odoo.addons.base.models.ir_config_parameter.IrConfigParameter.set_param') as set_param_mock:
            self.env['res.config.test'].create({}).execute()

        set_param_mock.assert_not_called()

    def test_config_parameter_falsy_values(self):
        settings = self.env['res.config.test'].create({
            'param1': 0,
            'param_bool': False,
        })
        settings.execute()

        IrConfigParameter = self.env['ir.config_parameter'].sudo()
        self.assertEqual(IrConfigParameter.get_param('resConfigTest.parameter1'), '0')
        self.assertEqual(IrConfigParameter.get_param('resConfigTest.parameter_bool'), 'False')

        settings = self.env['res.config.test'].create({})
        self.assertEqual(settings.param1, 0)
        self.assertFalse(settings.param_bool)
