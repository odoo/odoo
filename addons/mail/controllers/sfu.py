# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

# put that outside mail maybe ?
class SfuController(http.Controller):

    @http.route('/sfu/upload_transcription', type='http', auth='none', methods=['POST'], csrf=False)
    def sfu_upload_transcription(self, **kwargs):
        channel_uuid = kwargs.get('channel_uuid')
        uploaded_file = request.httprequest.files.get('file')

        if not channel_uuid or not uploaded_file:
            _logger.error("SFU upload request missing channel_uuid or file.")
            return request.make_response("Missing parameters.", status=400)

        channel = request.env['discuss.channel'].sudo().search([('sfu_channel_uuid', '=', channel_uuid)], limit=1)
        if not channel:
            _logger.error(f"SFU upload request for non-existent channel_uuid: {channel_uuid}")
            return request.make_response("Channel not found.", status=404)

        try:
            attachment = request.env['ir.attachment'].sudo().create({
                'name': f"transcription_{channel_uuid}.wav",
                'datas': base64.b64encode(uploaded_file.read()),
                'res_model': 'discuss.channel',
                'res_id': channel.id,
                'mimetype': 'audio/wav',
            })
            _logger.info(f"Successfully created attachment {attachment.id} for channel {channel.id}")
            # Optional: Post a message to the channel
            # channel.message_post(body=f"Recording saved: {attachment.name}")

        except Exception as e:
            _logger.error(f"Failed to create attachment for channel {channel.id}: {e}")
            return request.make_response("Error creating attachment.", status=500)

        return request.make_response("Success", status=200)
