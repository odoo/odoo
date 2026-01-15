# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from werkzeug.exceptions import NotFound

from odoo import http, _
from odoo.http import Controller, request, route, content_disposition
from odoo.tools import consteq, format_datetime


class EventController(Controller):

    @route(['''/event/<model("event.event"):event>/ics'''], type='http', auth="public")
    def event_ics_file(self, event, **kwargs):
        lang = request.env.context.get('lang', request.env.user.lang)
        if request.env.user._is_public():
            lang = request.cookies.get('frontend_lang')
        event = event.with_context(lang=lang)
        slot_id = int(kwargs['slot_id']) if kwargs.get('slot_id') else False
        files = event._get_ics_file(slot=request.env['event.slot'].sudo().browse(slot_id))
        if not event.id in files:
            return NotFound()
        content = files[event.id]
        return request.make_response(content, [
            ('Content-Type', 'application/octet-stream'),
            ('Content-Length', len(content)),
            ('Content-Disposition', content_disposition('%s.ics' % event.name))
        ])

    @route(['/event/<int:event_id>/my_tickets'], type='http', auth='public')
    def event_my_tickets(self, event_id, registration_ids, tickets_hash, badge_mode=False, responsive_html=False):
        """ Returns a pdf response, containing all tickets for attendees in registration_ids for event_id.

        Throw Forbidden if no registration is valid / hash is invalid / parameters are missing.
        This route is used in links in emails to attendees, as well as in registration confirmation screens.

        :param event: the id of prompted event. Only its attendees will be considered.
        :param registration_ids: ids of event.registrations of which tickets are generated
        :param tickets_hash: string hash used to access the tickets.
        :param badge_mode: boolean, True to use template of foldable badge instead of full page ticket.
        :param responsive_html: boolean, True if we want to see the a responsive html ticket.
        """
        registration_ids = json.loads(registration_ids or '[]')
        if not event_id or not tickets_hash or not registration_ids:
            raise NotFound()

        # We sudo the event in case of invitations sent before publishing it.
        event_sudo = request.env['event.event'].browse(event_id).exists().sudo()
        hash_truth = event_sudo and event_sudo._get_tickets_access_hash(registration_ids)
        if not hash_truth or not consteq(tickets_hash, hash_truth):
            raise NotFound()

        event_registrations_sudo = event_sudo.registration_ids.filtered(lambda reg: reg.id in registration_ids)
        report_name_prefix = _("Ticket") if responsive_html else _("Badges") if badge_mode else _("Tickets")
        report_date = format_datetime(request.env, event_registrations_sudo[0].event_begin_date, tz=event_sudo.date_tz, dt_format='medium')
        report_name = f"{report_name_prefix} - {event_sudo.name} ({report_date})"
        if len(event_registrations_sudo) == 1:
            report_name += f" - {event_registrations_sudo[0].name}"

        # sudo is necessary for accesses in templates.
        if responsive_html:
            html = request.env['ir.actions.report'].sudo()._render_qweb_html(
                'event.action_report_event_registration_responsive_html_ticket',
                event_registrations_sudo.ids,
            )[0]
            return request.make_response(html)

        pdf = request.env['ir.actions.report'].sudo()._render_qweb_pdf(
            'event.action_report_event_registration_badge' if badge_mode else
            'event.action_report_event_registration_full_page_ticket',
            event_registrations_sudo.ids,
        )[0]
        pdfhttpheaders = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(pdf)),
            ('Content-Disposition', content_disposition(f'{report_name}.pdf')),
        ]
        return request.make_response(pdf, headers=pdfhttpheaders)

    @http.route(['/event/init_barcode_interface'], type='jsonrpc', auth="user")
    def init_barcode_interface(self, event_id):
        event = request.env['event.event'].browse(event_id).exists() if event_id else False
        if event:
            return {
                'name': event.name,
                'country': event.address_id.country_id.name,
                'city': event.address_id.city,
                'company_name': event.company_id.name,
                'company_id': event.company_id.id
            }
        else:
            return {
                'name': _('Event Registrations'),
                'country': False,
                'city': False,
                'company_name': request.env.company.name,
                'company_id': request.env.company.id
            }
