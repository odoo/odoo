# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import logging
from json.decoder import JSONDecodeError
from requests.exceptions import RequestException

from odoo import api, fields, models, modules
from odoo.exceptions import UserError
from odoo.addons.ai.utils.llm_api_service import LLMApiService

_logger = logging.getLogger(__name__)

class DiscussCallRecording(models.Model):
    _name = 'discuss.call.recording'
    _description = 'Call Recording and Transcription'
    _order = 'create_date desc'

    name = fields.Char("Filename", required=True)
    call_history_id = fields.Many2one('discuss.call.history', string='Call History', required=True, ondelete='cascade', index=True)
    datas = fields.Binary('File')
    mimetype = fields.Char('Mimetype')
    transcript = fields.Text('Generated Transcript')
    transcription_status = fields.Selection(
        [
            ("pending", "Pending"),  # waiting for cron
            ("queued", "Queued"),  # picked by cron, might get stuck in this state
            ("done", "Done"),  # success
            ("error", "Error"),  # API failure
            ("too_big_to_process", "Too long to process"),  # >25 MB
            ("no_audio", "No audio"),  # attachment missing
        ],
        default="pending",
        copy=False,
        index=True,
    )

    @api.model
    def _cron_transcribe_recent_call_recording(self):
        record = self.search(
            [('transcription_status', '=', 'pending')],
            order='create_date desc',
            limit=1,
        )
        if not record:
            return

        record.transcription_status = 'queued'
        if not modules.module.current_test:
            self.env.cr.commit()

        if not record.datas:
            record.transcription_status = 'no_audio'
            return

        try:
            decoded_datas = base64.b64decode(record.datas)
            text = LLMApiService(self.env).get_transcription(decoded_datas, record.mimetype)
        except (RequestException, JSONDecodeError, UserError) as e:
            _logger.exception("Call Recording %s: transcription failed", record.id)
            record.transcription_status = 'error'
            return

        record.transcript = text
        record.transcription_status = 'done'
