# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import models, fields, tools, api

_logger = logging.getLogger(__name__)


class CloudStorageMigrationReport(models.Model):
    _name = 'cloud.storage.migration.report'
    _description = 'Cloud Storage Migration Report'
    _auto = False
    _order = 'message_sum_size, all_sum_size DESC'

    res_model = fields.Char(string='Model', readonly=True)
    res_model_name = fields.Char(string='Model Name', readonly=True, compute='_compute_res_model_name')

    message_sum_size = fields.Integer(string='Message Attachments Size (MB)', help="Total size in megabytes of all attachments linked to mail messages for this model", readonly=True)
    message_max_size = fields.Integer(string='Message Largest Attachment (MB)', help="Size in megabytes of the largest attachment linked to mail messages for this model", readonly=True)
    message_count = fields.Integer(string='Message Attachments Count', help="Total number of attachments linked to mail messages for this model", readonly=True)
    message_to_migrate = fields.Boolean(string='Message Attachments Migration', help="Indicates whether attachments linked to mail messages for this model are scheduled for cloud storage migration", compute='_compute_message_to_migrate')

    all_sum_size = fields.Integer(string='Total Attachments Size (MB)', help="Total size in megabytes of all attachments associated with records of this model", readonly=True)
    all_max_size = fields.Integer(string='Largest Attachment (MB)', help="Size in megabytes of the largest attachment associated with any record of this model", readonly=True)
    all_count = fields.Integer(string='Total Attachments Count', help="Total number of attachments associated with all records of this model", readonly=True)
    all_to_migrate = fields.Boolean(string='All Attachments Migration', help="Indicates whether all attachments associated with this model are scheduled for cloud storage migration", compute='_compute_all_to_migrate')

    has_attachment_rel = fields.Boolean(string='Has Attachment Field', help="Indicates whether this model has a relational field linking to ir.attachment model", compute='_compute_has_attachment_rel')

    def init(self):
        """Initialize the SQL view for the cloud storage migration report."""
        tools.drop_view_if_exists(self.env.cr, self._table)
        query = """
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    im.id AS id,
                    grouped.res_model AS res_model,
                    grouped.all_sum_size AS all_sum_size,
                    grouped.all_max_size AS all_max_size,
                    grouped.all_count AS all_count,
                    grouped.message_sum_size AS message_sum_size,
                    grouped.message_max_size AS message_max_size,
                    grouped.message_count AS message_count
                FROM (
                    SELECT
                        ia.res_model,
                        SUM(ia.file_size) / 1000000 AS all_sum_size,
                        MAX(ia.file_size) / 1000000 AS all_max_size,
                        COUNT(ia.id) AS all_count,
                        SUM(CASE WHEN mar.attachment_id IS NOT NULL THEN ia.file_size ELSE 0 END) / 1000000 AS message_sum_size,
                        MAX(CASE WHEN mar.attachment_id IS NOT NULL THEN ia.file_size ELSE 0 END) / 1000000 AS message_max_size,
                        COUNT(mar.attachment_id) AS message_count
                    FROM ir_attachment ia
                    LEFT JOIN message_attachment_rel mar
                        ON mar.attachment_id = ia.id
                    WHERE ia.res_field IS NULL
                        AND ia.res_id IS NOT NULL
                        AND ia.file_size IS NOT NULL
                        AND ia.res_model IS NOT NULL
                        AND ia.type = 'binary'
                    GROUP BY ia.res_model
                ) AS grouped
                INNER JOIN ir_model im ON im.model = grouped.res_model
            )
        """ % self._table
        self.env.cr.execute(query)

    @api.depends('res_model')
    def _compute_res_model_name(self):
        model_names = self.env['ir.model'].search_fetch([('model', 'in', self.mapped('res_model'))], ['model', 'name'])
        model_names = {model.model: model.name for model in model_names}
        for record in self:
            record.res_model_name = f"{model_names.get(record.res_model, 'unknown')} ({record.res_model})"

    @api.depends('res_model')
    def _compute_has_attachment_rel(self):
        for record in self:
            model_cls = self.env.registry.get(record.res_model)
            record.has_attachment_rel = model_cls and any(
                f for f in model_cls._fields.values() if f.relational and f.comodel_name == 'ir.attachment')

    def _compute_all_to_migrate(self):
        model_names = self.env['ir.config_parameter'].sudo().get_param('cloud_storage_migration_all_models', '').split(',')
        model_names = {m_ for m in model_names if (m_ := m.strip()) and m_ in self.env}
        for record in self:
            record.all_to_migrate = record.res_model in model_names

    def _compute_message_to_migrate(self):
        model_names = self.env['ir.config_parameter'].sudo().get_param('cloud_storage_migration_message_models', '').split(',')
        model_names = {m_ for m in model_names if (m_ := m.strip()) and m_ in self.env}
        for record in self:
            record.message_to_migrate = record.res_model in model_names

    def get_progress(self):
        max_attachment_id = int(self.env['ir.config_parameter'].get_param('cloud_storage_migration_max_attachment_id', 0)) or 1
        self.env.cr.execute("SELECT value FROM ir_config_parameter WHERE key = 'cloud_storage_migration_min_attachment_id'")
        min_attachment_id = int(self.env.cr.fetchone()[0]) if self.env.cr.rowcount else 0
        return min_attachment_id * 100 // max(max_attachment_id, min_attachment_id)
