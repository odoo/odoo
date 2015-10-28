# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import BadRequest

import odoo
from odoo import api, models, registry
from odoo.http import request


class ir_http(models.AbstractModel):
    _inherit = 'ir.http'

    def _auth_method_calendar(self):
        token = request.params['token']
        db = request.params['db']
        error_message = False
        with registry(db).cursor() as cr:
            env = api.Environment(cr, odoo.SUPERUSER_ID, context={})
            attendee = env['calendar.attendee'].search([('access_token', '=', token)], limit=1)
            if not attendee:
                error_message = """Invalid Invitation Token."""
            elif request.session.uid and request.session.login != 'anonymous':
                 # if valid session but user is not match
                user = env['res.users'].sudo().browse(request.session.uid)
                if attendee.partner_id.id != user.partner_id.id:
                    error_message = """Invitation cannot be forwarded via email. This event/meeting belongs to %s and you are logged in as %s. Please ask organizer to add you.""" % (attendee[0].email, user.email)

        if error_message:
            raise BadRequest(error_message)

        return True
