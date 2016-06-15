# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo import api, models, SUPERUSER_ID
from openerp.http import request
from openerp.api import Environment

from werkzeug.exceptions import BadRequest


class IrHttp(models.AbstractModel):

    _inherit = 'ir.http'

    def _auth_method_calendar(self):
        token = request.params['token']
        dbname = request.params['db']

        registry = odoo.modules.registry.RegistryManager.get(dbname)
        error_message = False
        with registry.cursor() as cr:
            env = Environment(cr, SUPERUSER_ID, {})

            attendee = env['calendar.attendee'].sudo().search([('access_token', '=', token)], limit=1)
            if not attendee:
                error_message = """Invalid Invitation Token."""
            elif request.session.uid and request.session.login != 'anonymous':
                # if valid session but user is not match
                user = env['res.users'].sudo().browse(request.session.uid)
                if attendee.partner_id != user.partner_id:
                    error_message = """Invitation cannot be forwarded via email. This event/meeting belongs to %s and you are logged in as %s. Please ask organizer to add you.""" % (attendee.email, user.email)
        if error_message:
            raise BadRequest(error_message)

        return True
