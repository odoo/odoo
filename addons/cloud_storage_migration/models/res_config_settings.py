# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields
from odoo.fields import Command


class CloudStorageMigrationSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    cloud_storage_migration_progress = fields.Integer(
        string='Migration Progress',
        help='Shows the progress of cloud storage migration (current/total)',
    )
    cloud_storage_migration_message_model_ids = fields.One2many(
        'ir.model',
        string="Message Attachments",
        help="Migrate Models' Message Attachments",
        inverse='_inverse_cloud_storage_migration_message_model_ids',
        store=False
    )
    cloud_storage_migration_message_models = fields.Char(
        config_parameter='cloud_storage_migration_message_models',
    )
    cloud_storage_migration_all_model_ids = fields.One2many(
        'ir.model',
        string="All Attachments",
        help="Migrate Models' All Attachments",
        inverse='_inverse_cloud_storage_migration_all_model_ids',
        store=False
    )
    cloud_storage_migration_all_models = fields.Char(
        config_parameter='cloud_storage_migration_all_models',
    )

    def get_values(self):
        res = super().get_values()
        res['cloud_storage_migration_progress'] = self.env['cloud.storage.migration.report'].get_progress()
        message_model_names = self.env['ir.config_parameter'].get_param('cloud_storage_migration_message_models', '').split(',')
        message_model_names = tuple(m_ for m in message_model_names if (m_ := m.strip()) and m_ in self.env)
        res['cloud_storage_migration_message_model_ids'] = [Command.set(self.env['ir.model'].search([('model', 'in', message_model_names)]).ids)]
        all_model_names = self.env['ir.config_parameter'].get_param('cloud_storage_migration_all_models', '').split(',')
        all_model_names = tuple(m_ for m in all_model_names if (m_ := m.strip()) and m_ in self.env)
        res['cloud_storage_migration_all_model_ids'] = [Command.set(self.env['ir.model'].search([('model', 'in', all_model_names)]).ids)]
        return res

    def _inverse_cloud_storage_migration_message_model_ids(self):
        self.cloud_storage_migration_message_models = ','.join(self.cloud_storage_migration_message_model_ids.mapped('model'))

    def _inverse_cloud_storage_migration_all_model_ids(self):
        self.cloud_storage_migration_all_models = ','.join(self.cloud_storage_migration_all_model_ids.mapped('model'))

    def action_open_cloud_storage_migration_configurations(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ir.config_parameter',
            'view_mode': 'list,form',
            'domain': [('key', 'in', [
                'cloud_storage_min_file_size',
                'cloud_storage_migration_max_file_size',
                'cloud_storage_migration_max_batch_file_size',
                'cloud_storage_migration_message_models',
                'cloud_storage_migration_all_models',
                'cloud_storage_migration_min_attachment_id',
                'cloud_storage_migration_max_attachment_id',
            ])],
            'target': 'current',
        }
