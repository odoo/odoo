# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestIrConfigParameter(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.IrConfigParameter = cls.env['ir.config_parameter']

        # Create a test cron with XMLID.
        cls.test_cron = cls.env['ir.cron'].create({
            'name': "Test Cron",
            'model_id': cls.env.ref('sale.model_sale_order').id,  # whatever
            'state': 'code',
            'code': '',
            'user_id': cls.env.uid,
            'interval_number': 1,
            'interval_type': 'days',
            'active': False,
        })
        cls.env['ir.model.data'].create({
            'name': 'test_cron',
            'model': 'ir.cron',
            'module': 'sale',
            'res_id': cls.test_cron.id,
        })

        # Patch `_get_param_cron_mapping` to include the test records.
        original_get_param_cron_mapping = cls.IrConfigParameter._get_param_cron_mapping

        def patched_get_param_cron_mapping(_self):
            mapping = original_get_param_cron_mapping()
            mapping['sale.test_param'] = 'sale.test_cron'
            return mapping

        _get_param_cron_mapping_patcher = patch(
            'odoo.addons.sale.models.ir_config_parameter.IrConfigParameter._get_param_cron_mapping',
            new=patched_get_param_cron_mapping,
        )
        cls.startClassPatcher(_get_param_cron_mapping_patcher)

    def test_creating_enabled_param_activates_cron(self):
        """Test cron synchronization when creating an enabled config parameter."""
        self.assertFalse(self.test_cron.active)
        self.IrConfigParameter.create({'key': 'sale.test_param', 'value': 'True'})
        self.assertTrue(self.test_cron.active)

    def test_creating_disabled_param_disables_cron(self):
        """Test cron synchronization when creating a disabled config parameter."""
        self.test_cron.active = True
        self.IrConfigParameter.create({'key': 'sale.test_param', 'value': 'False'})
        self.assertFalse(self.test_cron.active)

    def test_setting_enabled_param_value_activates_cron(self):
        """Test cron synchronization when updating to an enabled config parameter."""
        param = self.IrConfigParameter.create({'key': 'sale.test_param', 'value': 'False'})
        param.value = 'True'
        self.assertTrue(self.test_cron.active)

    def test_setting_disabled_param_value_disables_cron(self):
        """Test cron synchronization when updating to a disabled config parameter."""
        param = self.IrConfigParameter.create({'key': 'sale.test_param', 'value': 'True'})
        param.value = 'False'
        self.assertFalse(self.test_cron.active)

    def test_deleting_param_disables_cron(self):
        """Test cron synchronization when deleting a config parameter."""
        param = self.IrConfigParameter.create({'key': 'sale.test_param', 'value': 'True'})
        param.unlink()
        self.assertFalse(self.test_cron.active)

    def test_non_mapped_param_has_no_effect_on_cron(self):
        """Test that non-mapped parameter don't affect crons."""
        self.IrConfigParameter.create({'key': 'sale.non_mapped_param', 'value': 'True'})
        self.assertFalse(self.test_cron.active)
