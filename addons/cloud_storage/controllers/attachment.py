# Part of Odoo. See LICENSE file for full copyright and licensing details.

import requests

from odoo import _
from odoo.http import request
from odoo.addons.mail.controllers.attachment import AttachmentController
from odoo.addons.mail.tools.discuss import mail_route


class CloudAttachmentController(AttachmentController):
    def _make_zip(self, name, attachments):
        # ZIP files need the attachment bytes rather than a cloud redirect.
        return super()._make_zip(name, attachments.with_context(cloud_storage_force_download=True))

    def _get_text_attachment_content(self, attachment, head=False):
        if not (info := attachment._get_download_info()):
            return super()._get_text_attachment_content(attachment, head)
        # Thumbnails only need the first bytes of the file.
        headers = {'Range': f'bytes=0-{self.TEXTUAL_THUMBNAIL_SIZE - 1}'} if head else None
        response = requests.get(info['url'], headers=headers, timeout=10)
        response.raise_for_status()
        return response.content[:self.TEXTUAL_THUMBNAIL_SIZE] if head else response.content

    @mail_route()
    def mail_attachment_upload(self, ufile, thread_id, thread_model, is_pending=False, **kwargs):
        is_cloud_storage = kwargs.get('cloud_storage')
        if (is_cloud_storage and not request.env['ir.config_parameter'].sudo().get_str('cloud_storage_provider')):
            return request.make_json_response({
                'error': _('Cloud storage configuration has been changed. Please refresh the page.')
            })

        response = super().mail_attachment_upload(ufile, thread_id, thread_model, is_pending, **kwargs)

        if not is_cloud_storage:
            return response

        data = response.json
        if data.get("error"):
            return response

        # append upload url to the response to allow the client to directly
        # upload files to the cloud storage
        attachment = request.env["ir.attachment"].browse(data["data"]["attachment_id"]).sudo()
        data["upload_info"] = attachment._generate_cloud_storage_upload_info()
        return request.make_json_response(data)
