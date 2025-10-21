# Part of Odoo. See LICENSE file for full copyright and licensing details.

import requests
import uuid

from odoo import models, fields, _
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.http import Stream, request
from odoo.tools import ormcache

from .res_config_settings import DEFAULT_CLOUD_STORAGE_MIN_FILE_SIZE

import logging

logger = logging.getLogger(__name__)


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'
    _cloud_storage_upload_url_time_to_expiry = 300  # 300 seconds
    _cloud_storage_download_url_time_to_expiry = 300  # 300 seconds

    type = fields.Selection(
        selection_add=[('cloud_storage', 'Cloud Storage')],
        ondelete={'cloud_storage': 'set url'}
    )

    def _to_http_stream(self):
        if (self.type == 'cloud_storage' and
              self.env['res.config.settings']._get_cloud_storage_configuration()):
            self.ensure_one()
            info = self._generate_cloud_storage_download_info()
            stream = Stream(type='url', url=info['url'])
            if 'time_to_expiry' in info:
                # cache the redirection until 10 seconds before the expiry
                stream.max_age = max(info['time_to_expiry'] - 10, 0)
            return stream
        return super()._to_http_stream()

    def _post_add_create(self, **kwargs):
        super()._post_add_create(**kwargs)
        if kwargs.get('cloud_storage'):
            if not self.env['ir.config_parameter'].sudo().get_str('cloud_storage_provider'):
                raise UserError(_('Cloud Storage is not enabled'))
            for record in self:
                record.write({
                    'raw': False,
                    'type': 'cloud_storage',
                    'url': record._generate_cloud_storage_url(),
                })

    def _generate_cloud_storage_blob_name(self):
        """
        Generate a unique blob name for the attachment

        :return: A unique blob name str
        """
        return f'{self._origin.id}/{uuid.uuid4()}/{self.name}'

    # Implement the following methods for each cloud storage provider.
    def _generate_cloud_storage_url(self):
        """
        Generate a cloud blob url without signature or token for the attachment.
        This url is only used to identify the cloud blob.

        :return: A cloud blob url str
        """
        raise NotImplementedError()

    def _generate_cloud_storage_download_info(self):
        """
        Generate the download info for the public client to directly download
        the attachment's blob from the cloud storage.

        :return: An download_info dictionary containing:

            download_url
                cloud storage url with permission to download the file
            time_to_expiry
                the time in seconds before the download url expires
        """
        raise NotImplementedError()

    def _generate_cloud_storage_upload_info(self):
        """
        Generate the upload info for the public client to directly upload a
        file to the cloud storage.

        :return: An upload_info dictionary containing:

            upload_url
                cloud storage url with permission to upload the file
            method
                the request method used to upload the file
            response_status
                the status of the response for a successful upload request
            [Optionally] headers
                a dictionary of headers to be added to the upload request
        """
        raise NotImplementedError()

    @ormcache()
    def _get_cloud_storage_unsupported_models(self):
        # Some models may use their attachments' data in the business code
        # We should avoid those attachments to be uploaded to the cloud storage
        models = self.env.registry.descendants(['mail.thread.main.attachment'], '_inherit', '_inherits')
        if 'documents.mixin' in self.env:
            models.update(self.env.registry.descendants(['documents.mixin'], '_inherit'))
            models.add('documents.document')
        return list(models)

    def _cron_upload_to_cloud_storage(self):
        """
        A cron job designed to be manually triggered from UI

        The Http server only mark the cron job as partially finished without uploading any attachments.
        The cron job will be rescheduled asap and continue the upload process stopped at the last time.

        The cron job uses the info in the last ir.cron.progress record to continue the upload process.
        The cron job will stop uploading if there is no time left.
        """
        if not self.env['ir.config_parameter'].sudo().get_str('cloud_storage_provider'):
            return
        progress = self.env['ir.cron.progress'].sudo().browse(self.env.context.get('ir_cron_progress_id'))
        if not progress:
            return
        last_progress = self.env['ir.cron.progress'].search([('cron_id', '=', progress.cron_id.id), ('id', '<', progress.id)], limit=1, order='id desc')

        # NOTE: ir.cron.progress is garbage collected after 1 week

        # use the progress to log the whole logging process to avoid
        # 1. updating ir.config_parameter which will invaidate ormcache
        # 2. creating extra model

        # The id of the attachment that was last attempted to be uploaded
        min_id = last_progress.done
        max_id = int(self.search([], limit=1, order='id desc').id)
        # Maximum attachment id - id of the last attachment that was attempted to be uploaded
        # non existing (deleted) attachments are logicically treated as tasks but auto skipped by the code
        remaining = max_id - last_progress.done

        time_left = self.env['ir.cron']._commit_progress(processed=last_progress.done, remaining=remaining)
        if request:
            # don't upload, if the method is called by ``Manually Run`` button from web client
            # cron job is partially done, it will be rescheduled asap in cron server
            return

        if not time_left:
            return

        has_ai_discuss_channel = 'ai_chat' in [t for t, _ in self.env['discuss.channel']._fields['channel_type'].selection]
        has_documents = 'documents.document' in self.env
        for i in range(100):
            attachment = self.search(
                (
                    self._get_domain_to_upload_to_cloud_storage() &
                    # Domain('create_date', '<', fields.Datetime.now() - timedelta(days=90)) &
                    Domain('id', '>', min_id) &
                    Domain('id', '<=', max_id)
                ),
                limit=1,
                order='id asc'
            )

            min_id = attachment.id

            if not attachment:
                # all attachments have been processed
                self.env['ir.cron']._commit_progress(processed=max_id - progress.done, remaining=0)
                return

            if not i:
                # reschedule the cron job asap in case the process is killed because of timeout
                self.env['ir.cron']._reschedule_asap({'id': progress.cron_id.id})

            if has_documents:
                Documents = self.env['documents.document'].sudo().with_context(active_test=False)
                if Documents.search([('attachment_id', '=', attachment.id)]):
                    self.env['ir.cron']._commit_progress(processed=attachment.id - progress.done, remaining=max_id - attachment.id)
                    # skip the attachment if it is also used by documents
                    continue
            if has_ai_discuss_channel and attachment.res_model == 'discuss.channel':
                if self.env['discuss.channel'].sudo().browse(attachment.res_id).sudo().channel_type == 'ai_chat':
                    self.env['ir.cron']._commit_progress(processed=attachment.id - progress.done, remaining=max_id - attachment.id)
                    # skip the attachment if it is used by an ai discuss channel
                    continue

            # commit progress before upload to upload file only once even if it timeout
            self.env['ir.cron']._commit_progress(processed=attachment.id - progress.done, remaining=max_id - attachment.id)

            try:
                attachment._upload_to_cloud_storage()
                logger.info('uploaded attachment %s to cloud storage', attachment.id)
            except Exception as e:  # noqa: BLE001
                logger.error('Failed to upload attachment %s to cloud storage: %s', attachment.id, e)
                # in case the records is modified by another transaction concurrently
                self.env.invalidate_all(flush=False)

            time_left = self.env['ir.cron']._commit_progress(0)
            if not time_left:
                break

    @ormcache()
    def _get_domain_to_upload_to_cloud_storage(self):
        registry = self.env.registry
        MainThread = registry['mail.thread']
        unsupported_models = set(self._get_cloud_storage_unsupported_models())
        model_names = [
            model_name for model_name, model_class in registry.items()
            if issubclass(model_class, MainThread)
            and issubclass(model_class, models.Model)
            and model_name not in unsupported_models
        ]
        model_names = [m[0] for m in self.env['ir.ui.view']._read_group(
            [('model', 'in', model_names), ('type', '=', 'form')], groupby=['model'])]
        if 'discuss.channel' not in model_names:
            model_names.append('discuss.channel')
        domain = (
            # ignore if attachment is already a cloud storage attachment
            Domain('type', '=', 'binary') &
            # ignore if attachment is too small
            Domain('file_size', '>', self.env['ir.config_parameter'].sudo().get_int('cloud_storage_min_file_size', DEFAULT_CLOUD_STORAGE_MIN_FILE_SIZE)) &
            # ignore if attachment is not supported by cloud storage
            Domain('res_model', 'in', model_names) &
            # ignore if attachment doesn't have a record
            Domain('res_id', '!=', False) &
            # ignore if attachment is for a field
            Domain('res_field', '=', False)
        )
        return domain

    def _upload_to_cloud_storage(self):
        for attachment in self:
            attachment_ = self.new(origin=attachment)
            attachment_.url = attachment_._generate_cloud_storage_url()
            upload_info = attachment_._generate_cloud_storage_upload_info()
            data = attachment.raw
            headers = upload_info.get('headers', {})
            match upload_info['method'].lower():
                case 'put':
                    upload_method = requests.put
                case 'post':
                    upload_method = requests.post
                case _:
                    raise Exception(f'Invalid method: {upload_info['method']}')
            # upload rate limit can be set by nginx proxy for
            # google cloud storage or azure blob storage by url matching
            response = upload_method(upload_info['url'], data=data, headers=headers)
            if response.status_code != upload_info['response_status']:
                raise Exception(f'Failed to upload attachment {attachment.id} to cloud storage: {response.status_code}')
            attachment.write({
                'type': 'cloud_storage',
                'url': attachment_.url,
                'raw': False,
            })
