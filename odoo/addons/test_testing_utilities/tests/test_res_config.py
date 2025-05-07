from unittest.mock import patch

from odoo.tests.common import TransactionCase


class TestResConfig(TransactionCase):
    def test_config_parameter_with_default_value(self):
        self.env['res.config.test'].create({}).execute()

        self.assertEqual(
            self.env['ir.config_parameter'].get_param('resConfigTest.parameter_with_default'),
            str(1000),
            "The parameter must be saved with its default value",
        )

        # The parameter is already saved in the ir_config_parameter table.
        with patch('odoo.addons.base.models.ir_config_parameter.IrConfig_Parameter.set_param') as set_param_mock:
            self.env['res.config.test'].create({}).execute()

        set_param_mock.assert_not_called()
