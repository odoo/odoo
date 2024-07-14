# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request
from odoo.tools import html2plaintext


class HelpdeskClientController(http.Controller):

    @http.route('/mail_plugin/ticket/create', type='json', auth='outlook',
                cors="*")
    def helpdesk_ticket_create(self, partner_id, email_body, email_subject):
        partner = request.env['res.partner'].browse(partner_id).exists()
        if not partner:
            return {'error': 'partner_not_found'}

        record = request.env['helpdesk.ticket'].with_company(partner.company_id).create({
            'name': html2plaintext(email_subject),
            'partner_id': partner_id,
            'description': email_body,
            'user_id': request.env.uid,
            # we don't rely on default values because we want to trigger the ticket acknowledgement email
            # there is an advanced processing on the "create" method to determine the stage based on the team
            # (see 'helpdesk.ticket#create' and 'helpdesk.ticket#_track_template')
            'team_id': request.env['helpdesk.ticket']._default_team_id(),
        })

        return {'ticket_id': record.id}
