# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields

class DiscussCallRecording(models.Model):
    _name = 'discuss.call.recording'
    _description = 'Call Recording and Transcription'
    _order = 'create_date desc'

    name = fields.Char("Filename", required=True)
    call_history_id = fields.Many2one('discuss.call.history', string='Call History', required=True, ondelete='cascade', index=True)
    datas = fields.Binary('File')
    mimetype = fields.Char('Mimetype')
    transcription = fields.Text('Transcription')
