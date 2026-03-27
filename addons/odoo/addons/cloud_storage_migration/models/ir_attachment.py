# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import time
import requests

from datetime import timedelta

from odoo.tools import SQL, config
from odoo.http import request
from odoo import models, fields, _
from odoo.exceptions import UserError, ValidationError

from odoo.addons.base.models.ir_module import assert_log_admin_access
from odoo.addons.cloud_storage.models.res_config_settings import DEFAULT_CLOUD_STORAGE_MIN_FILE_SIZE


_logger = logging.getLogger(__name__)


class CloudStorageAttachmentMigration(models.Model):
    _inherit = 'ir.attachment'

    def _migrate_local_to_cloud_storage(self, session):
        """Migrate attachment from local binary storage to cloud storage"""
        if self.type != 'binary':
            raise ValidationError(_("Attachment (%s) is not a binary attachment and cannot be migrated to cloud storage.", self.id))
        if not self.store_fname:
            raise ValidationError(_("Attachment (%s) does not have a stored filename and cannot be migrated to cloud storage.", self.id))
        filepath = self._full_path(self.store_fname)
        self.url = self._generate_cloud_storage_url()
        upload_info = self._generate_cloud_storage_upload_info()
        headers = upload_info.get('headers')
        with open(filepath, 'rb') as f:
            # upload rate limit can be set by nginx proxy for
            # google cloud storage or azure blob storage by url matching
            response = session.request(upload_info['method'], upload_info['url'], data=f, headers=headers, timeout=(10, 30))
            if response.status_code != upload_info['response_status']:
                raise ValidationError(f'Failed to upload attachment {self.id} to cloud storage: {response.status_code}')
        self.write({
            'type': 'cloud_storage',
            'mimetype': self.mimetype,  # force kept the mimetype
            'raw': False,
        })

    @assert_log_admin_access
    def _cron_migrate_local_to_cloud_storage(self):
        """
        The Http server only reschedules the cron job asap without migrating any attachment.
        The cron server will continue the migrating process stopped at the last time by using
        ``cloud_storage_migration_min_attachment_id``
        """
        ICP = self.env['ir.config_parameter']
        if not ICP.get_param('cloud_storage_provider'):
            raise UserError(_("Cloud storage provider is not configured"))

        # check ir.config_parameter values' formats are correct
        cron = self.env.ref('cloud_storage_migration.ir_cron_manual_migrate_local_to_cloud_storage')
        min_file_size = int(ICP.get_param('cloud_storage_min_file_size', DEFAULT_CLOUD_STORAGE_MIN_FILE_SIZE))
        max_file_size = int(ICP.get_param('cloud_storage_migration_max_file_size', 10**9))  # default 1GB
        max_batch_file_size = int(ICP.get_param('cloud_storage_migration_max_batch_file_size', 10**10))  # default 10GB
        message_model_names = ICP.get_param('cloud_storage_migration_message_models', '').split(',')
        message_model_names = tuple(m_ for m in message_model_names if (m_ := m.strip()) and m_ in self.env)
        all_model_names = ICP.get_param('cloud_storage_migration_all_models', '').split(',')
        all_model_names = tuple(m_ for m in all_model_names if (m_ := m.strip()) and m_ in self.env)
        if not message_model_names and not all_model_names:
            raise UserError(_("No model for cloud storage migration"))

        max_attachment_id = int(ICP.get_param('cloud_storage_migration_max_attachment_id', 0))
        if not max_attachment_id:
            max_attachment_id = self.env['ir.attachment'].sudo().search_fetch([], ['id'], limit=1, order='id desc').id or 1
            ICP.set_param('cloud_storage_migration_max_attachment_id', max_attachment_id)

        if request:
            # Don't upload in HTTP server, if the method is called by ``Manually Run`` button from web client
            # The cron job should be rescheduled asap in cron server
            cron._trigger()
            return

        def commit_min_attachment_id(attachment_id):
            # directly write data of ir_config_parameter to avoid invalidating ormcache
            self.env.cr.execute("UPDATE ir_config_parameter SET value = %s WHERE key = 'cloud_storage_migration_min_attachment_id'", (str(attachment_id),))
            self.env.cr.commit()

        limit_time_real = config['limit_time_real']
        # ``config['limit_time_real_cron'] == 0`` means unlimited time for cron worker,
        # but will fallback to ``config['limit_time_real']`` for cron thread
        # here we use ``config['limit_time_real']`` for simplicity
        if config['limit_time_real_cron'] and config['limit_time_real_cron'] > 0:
            limit_time_real = config['limit_time_real_cron']
        # use half of the time limit to mitigate the timeout problem
        end_time = limit_time_real // 2 + time.monotonic()

        check_model = []
        if message_model_names:
            check_model.append(SQL('(ia.res_model IN %s AND mar.attachment_id IS NOT NULL)', message_model_names))
        if all_model_names:
            check_model.append(SQL('(ia.res_model IN %s)', all_model_names))
        check_model = SQL(' OR ').join(check_model)

        check_documents = SQL("""
            AND NOT EXISTS (
                SELECT 1
                FROM documents_document dd
                WHERE dd.attachment_id = ia.id
            )""") if 'documents.document' in self.env else SQL("")

        # check ir_attachment records which are used by any mail_message.attachment_ids
        query = SQL("""
            WITH last_attachment AS (
                SELECT value::integer AS id
                FROM ir_config_parameter
                WHERE key = 'cloud_storage_migration_min_attachment_id'
                LIMIT 1
            )
            SELECT ia.id
            FROM ir_attachment ia
            LEFT JOIN message_attachment_rel mar
            ON mar.attachment_id = ia.id
            WHERE ia.id <= %(max_attachment_id)s
            AND ia.id > COALESCE((SELECT id FROM last_attachment), 0)
            AND ia.type = 'binary'
            AND ia.url IS NULL
            AND ia.res_id IS NOT NULL
            AND ia.res_field IS NULL
            AND ia.store_fname IS NOT NULL
            AND (%(check_model)s)
            AND ia.file_size BETWEEN %(min_file_size)s AND %(max_file_size)s
            AND ia.create_date < %(create_date)s
            %(check_documents)s
            ORDER BY ia.id ASC
            LIMIT 1;
        """,
            max_attachment_id=max_attachment_id,
            check_model=check_model,
            # ignore if attachment is too small or too large
            min_file_size=min_file_size,
            max_file_size=max_file_size,
            # ignore attachments uploaded recently in case their binaries are unfortunately used by business
            # codes which may block important business operations
            create_date=fields.Datetime.now() - timedelta(days=7),
            # ignore if attachment is used by documents.document
            check_documents=check_documents,
        )

        session = requests.Session()

        total_file_size = 0
        first_attachment = True
        while True:
            self.env.cr.execute(query)
            res = self.env.cr.fetchone()
            attachment = self.env['ir.attachment'].browse(res[0] if res else False)

            if not attachment:
                commit_min_attachment_id(max_attachment_id)
                return

            total_file_size += attachment.file_size
            if max_batch_file_size and total_file_size >= max_batch_file_size:
                if first_attachment:
                    # skip in case attachment.file_size > max_batch_file_size
                    commit_min_attachment_id(attachment.id)
                break
            first_attachment = False

            # commit before migration to upload the file only once even if it causes timeout
            commit_min_attachment_id(attachment.id)

            try:
                attachment._migrate_local_to_cloud_storage(session)
                self.env.cr.commit()
                _logger.info('uploaded attachment %s to cloud storage', attachment.id)
            except Exception as e:  # noqa: BLE001
                _logger.warning('Failed to upload attachment %s to cloud storage: %s', attachment.id, e)
                self.env.cr.rollback()

            if end_time < time.monotonic():
                break

        cron._trigger()
