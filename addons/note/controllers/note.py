# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request


class NoteController(http.Controller):

    @http.route('/note/new', type='json', auth='user')
    def note_new_from_systray(self, note, activity_type_id=None, date_deadline=None):
        """ Route to create note and their activity directly from the systray """
        note = request.env['note.note'].create({'memo': note})
        if date_deadline:
            activity_values = {
                'note': note.memo,
                'date_deadline': date_deadline,
                'res_model_id': request.env.ref("note.model_note_note").id,
                'res_id': note.id,
                'note_id': note.id,
            }
            if not activity_type_id:
                activity_type_id = request.env['mail.activity.type'].sudo().search([('category', '=', 'reminder')], limit=1).id
            if activity_type_id:
                activity_values['activity_type_id'] = activity_type_id
            request.env['mail.activity'].create(activity_values)
        return note.id
