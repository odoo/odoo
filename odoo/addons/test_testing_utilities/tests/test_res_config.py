# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from unittest.mock import patch
from odoo.tests.common import TransactionCase

class TestResConfig(TransactionCase):

    def test_00_add_parameter_with_default_value(self):
        """ Check if parameters with a default value are saved in the ir_config_parameter table """

        self.env['res.config.test'].create({}).execute()
        self.assertEqual(self.env['ir.config_parameter'].sudo().get_int('resConfigTest.parameter1'), 1000,
            "The parameter is not saved with its default value")

        with patch('odoo.addons.base.models.ir_config_parameter.IrConfig_Parameter.create') as create_param_mock:
            with patch('odoo.addons.base.models.ir_config_parameter.IrConfig_Parameter.write') as write_param_mock:
                self.env['res.config.test'].create({}).execute()

        create_param_mock.assert_not_called()
        write_param_mock.assert_not_called()
