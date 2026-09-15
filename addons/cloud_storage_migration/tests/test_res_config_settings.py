# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestCloudStorageMigrationResConfigSettings(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ResConfigSettings = cls.env['res.config.settings']
        cls.model_partner = cls.env['ir.model'].search([('model', '=', 'res.partner')], limit=1)
        cls.model_users = cls.env['ir.model'].search([('model', '=', 'res.users')], limit=1)

    def _simulate_web_save_x2many_update(self, field_name, new_records):
        """Simulate res.config.settings save from the web client.

        web_save always creates a new record. When the user removes records from
        a non-stored x2many field, the web client sends link commands for the
        remaining records instead of a set command.
        """
        commands = [Command.link(record.id) for record in new_records]
        settings = self.ResConfigSettings.create({field_name: commands})
        settings.execute()

    def test_remove_message_model_from_settings(self):
        """Removing a model from settings must update the config parameter."""
        settings = self.ResConfigSettings.create({})
        settings.cloud_storage_migration_message_model_ids = self.model_partner | self.model_users
        settings.execute()
        self.assertEqual(
            set(self.env['ir.config_parameter'].sudo().get_param('cloud_storage_migration_message_models').split(',')),
            {'res.partner', 'res.users'},
        )

        self._simulate_web_save_x2many_update('cloud_storage_migration_message_model_ids', self.model_partner)
        self.assertEqual(
            self.env['ir.config_parameter'].sudo().get_param('cloud_storage_migration_message_models'),
            'res.partner',
        )

    def test_remove_all_model_from_settings(self):
        """Removing a model from the all-attachments field must update the config parameter."""
        settings = self.ResConfigSettings.create({})
        settings.cloud_storage_migration_all_model_ids = self.model_partner | self.model_users
        settings.execute()
        self.assertEqual(
            set(self.env['ir.config_parameter'].sudo().get_param('cloud_storage_migration_all_models').split(',')),
            {'res.partner', 'res.users'},
        )

        self._simulate_web_save_x2many_update('cloud_storage_migration_all_model_ids', self.model_partner)

        self.assertEqual(
            self.env['ir.config_parameter'].sudo().get_param('cloud_storage_migration_all_models'),
            'res.partner',
        )
