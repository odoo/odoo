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

        call_history = request.env['discuss.call.history'].sudo().search([
            ('channel_id', '=', channel.id),
            ('end_dt', '=', False)
        ], order='start_dt DESC', limit=1)

        if not call_history:
            _logger.error(f"SFU upload request for channel {channel.id} with no active call history.")
            return request.make_response("Active call history not found for the channel.", status=404)

        try:
            recording = request.env['discuss.call.recording'].sudo().create({
                'name': f"recording_{channel_uuid}.wav",
                'call_history_id': call_history.id,
                'datas': base64.b64encode(uploaded_file.read()),
                'mimetype': 'audio/wav',
                'transcription_status': 'pending',
            })
            _logger.info(f"Successfully created recording {recording.id} for call history {call_history.id}")

        except Exception as e:
            _logger.error(f"Failed to create recording for call history {call_history.id}: {e}")
            return request.make_response("Error creating recording.", status=500)

        try:
            request.env.ref("mail.ir_cron_transcribe_recent_call_recording").sudo()._trigger()
        except Exception as e:
            _logger.error(f"Failed to trigger transcription for call history {call_history.id}: {e}")

        return request.make_response("Success", status=200)
