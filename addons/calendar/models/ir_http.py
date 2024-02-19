# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import BadRequest

from odoo import models
from odoo.http import request


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _auth_method_calendar(cls):
        token = request.httprequest.args.get('token', '')

        error_message = False

        attendee = request.env['calendar.attendee'].sudo().search([('access_token', '=', token)], limit=1)
        if not attendee:
            error_message = """Invalid Invitation Token."""
        elif request.session.uid and request.session.login != 'anonymous':
            # if valid session but user is not match
            user = request.env['res.users'].sudo().browse(request.session.uid)
            if attendee.partner_id != user.partner_id:
                error_message = """Invitation cannot be forwarded via email. This event/meeting belongs to %s and you are logged in as %s. Please ask organizer to add you.""" % (attendee.email, user.email)
        if error_message:
            raise BadRequest(error_message)

        cls._auth_method_public()
