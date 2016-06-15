# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import openerp
from openerp.osv import osv
from openerp.http import request

from werkzeug.exceptions import BadRequest


class ir_http(osv.AbstractModel):
    _inherit = 'ir.http'

    def _auth_method_calendar(self):
        token = request.params['token']
        db = request.params['db']

        registry = openerp.modules.registry.RegistryManager.get(db)
        attendee_pool = registry.get('calendar.attendee')
        error_message = False
        with registry.cursor() as cr:
            attendee_id = attendee_pool.search(cr, openerp.SUPERUSER_ID, [('access_token', '=', token)])
            if not attendee_id:
                error_message = """Invalid Invitation Token."""
            elif request.session.uid and request.session.login != 'anonymous':
                 # if valid session but user is not match
                attendee = attendee_pool.browse(cr, openerp.SUPERUSER_ID, attendee_id[0])
                user = registry.get('res.users').browse(cr, openerp.SUPERUSER_ID, request.session.uid)
                if attendee.partner_id.id != user.partner_id.id:
                    error_message = """Invitation cannot be forwarded via email. This event/meeting belongs to %s and you are logged in as %s. Please ask organizer to add you.""" % (attendee.email, user.email)

        if error_message:
            raise BadRequest(error_message)

        return True
