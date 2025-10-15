# Part of Odoo. See LICENSE file for full copyright and licensing details.

import uuid

from odoo import models, fields, _
from odoo.exceptions import UserError
from odoo.http import Stream


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
            if not self.env['ir.config_parameter'].sudo().get_param('cloud_storage_provider'):
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
        return f'{self.id}/{uuid.uuid4()}/{self.name}'

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

    def _get_cloud_storage_unsupported_models(self):
        # Some models may use their attachments' data in the business code
        # We should avoid those attachments to be uploaded to the cloud storage
        models = self.env.registry.descendants(['mail.thread.main.attachment'], '_inherit', '_inherits')
        if 'documents.mixin' in self.env:
            models.update(self.env.registry.descendants(['documents.mixin'], '_inherit'))
            models.add('documents.document')
        return list(models)
