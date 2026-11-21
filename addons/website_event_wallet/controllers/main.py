# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from datetime import timezone

from werkzeug.exceptions import NotFound

from odoo import http
from odoo.addons.website_event.controllers.main import WebsiteEventController
from odoo.http import request
from odoo.http.stream import content_disposition
from odoo.tools import consteq, html2plaintext
from odoo.tools.misc import get_lang


class WebsiteEventWalletController(WebsiteEventController):

    @http.route(
        '/event/<int:event_id>/registration/<int:registration_id>/wallet/<string:provider_code>',
        type='http', auth='public', methods=['GET'], website=True, sitemap=False,
    )
    def registration_wallet(self, event_id, registration_id, provider_code, tickets_hash=None, **kwargs):
        """Download one pass after validating Odoo's signed ticket access link."""
        # Ticket links authorize access to this exact event/registration pair.
        event = request.env['event.event'].sudo().browse(event_id).exists()
        if not event or not tickets_hash:
            raise NotFound()
        if not consteq(tickets_hash, event._get_tickets_access_hash([registration_id])):
            raise NotFound()
        if not event.company_id.allow_add_to_wallet:
            raise NotFound()
        registration = request.env['event.registration'].sudo().search([
            ('id', '=', registration_id), ('event_id', '=', event.id),
            ('state', 'in', ['open', 'done']),
        ], limit=1)
        certificate = self._get_wallet_certificate(event, provider_code)
        if not registration or not certificate:
            raise NotFound()
        lang = get_lang(request.env).code
        registration = registration.with_context(lang=lang)
        event = event.with_context(lang=lang)
        address = event.address_id
        event_data = {
            'event_name': event.name,
            'attendee': registration.name,
            'ticket_type': registration.event_ticket_id.name or request.env._("General Admission"),
            'start': registration.event_begin_date.replace(tzinfo=timezone.utc).isoformat(),
            'end': registration.event_end_date.replace(tzinfo=timezone.utc).isoformat(),
            'venue': address.name or '',
            'city': address.city or '',
            'room': '',
            'barcode': registration.barcode,
            'registration_id': str(registration.id),
            'instructions': html2plaintext(event.ticket_instructions or ''),
            'subtitle': event.subtitle or '',
            'organizer': event.organizer_id.name or '',
            'address': ', '.join(filter(None, [
                address.street, address.street2, address.city,
                address.state_id.name, address.zip, address.country_id.name,
            ])),
            'event_url': event.get_base_url() + event.website_url,
            'timezone': event.date_tz or 'UTC',
            'background_image': event.wallet_background_image.content if event.wallet_background_image else None,
            'primary_color': event.company_id.primary_color or '#162A44',
            'secondary_color': event.company_id.secondary_color or '#77E1D3',
        }
        # The provider is selected server-side for the current website/company.
        # Elevated access is needed only to read its protected signing material.
        wallet_pass = certificate._generate_wallet_event_pass(
            event_data, provider_code=provider_code,
            code_type='barcode' if event.use_barcode else 'qr',
            lang=lang,
        )
        payload = base64.b64decode(wallet_pass['content'])
        return request.make_response(payload, headers=[
            ('Content-Type', wallet_pass['mimetype']),
            ('Content-Disposition', content_disposition('ticket-%s.%s' % (registration.id, wallet_pass['extension']))),
            ('Content-Length', str(len(payload))),
            ('Cache-Control', 'private, no-store'),
            ('X-Content-Type-Options', 'nosniff'),
        ])

    def _get_wallet_certificate(self, event, provider_code):
        """Resolve the certificate from the current website's company only."""
        website = request.env.website
        Certificate = request.env['certificate.certificate']
        if not website or event.company_id != website.company_id or not website.company_id.allow_add_to_wallet:
            return Certificate
        # The signed ticket route needs signing material unavailable to visitors.
        # Company and provider scope are fixed server-side before elevating.
        return Certificate.sudo()._get_wallet_certificate(website.company_id, provider_code)

    def _get_registration_confirm_values(self, event, attendees_sudo):
        values = super()._get_registration_confirm_values(event, attendees_sudo)
        website = request.env.website
        values['wallet_providers'] = []
        if website and event.company_id == website.company_id:
            # Expose provider codes only, never certificate records or keys.
            values['wallet_providers'] = website.company_id.sudo()._get_available_wallet_providers()
        return values
