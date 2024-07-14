# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from urllib.parse import unquote_plus
from werkzeug.exceptions import NotFound

from odoo import http
from odoo.addons.account_payment.controllers import portal as account_payment_portal
from odoo.addons.base.models.ir_qweb import keep_query
from odoo.http import request


class AppointmentAccountPaymentPortal(account_payment_portal.PaymentPortal):

    @http.route('/appointment/<int:appointment_type_id>/invoice/<string:invoice_token>/post_payment',
                type='http', auth="public", website=True, sitemap=False)
    def appointment_post_payment(self, appointment_type_id, invoice_token, **kwargs):
        """ Landing route of the payment flow in the case of an appointment booking.
            Redirects to event page if the event was created after successful booking payment or
            to booking page if event is not created (payment failure or pending, for instance) """
        invoice_sudo = request.env['account.move'].sudo().search([('access_token', '=', invoice_token)], limit=1)
        if not invoice_sudo:
            raise NotFound()

        # Should be a singleton functionally
        booking = invoice_sudo.calendar_booking_ids
        if not booking:
            raise NotFound()

        invitation_parameters = booking.appointment_invite_id._get_invitation_url_parameters()
        if booking.calendar_event_id:
            return request.redirect(
                "/calendar/view/{event_token}?partner_id={pid}&{args}".format(
                    event_token=booking.calendar_event_id.access_token,
                    pid=invoice_sudo.partner_id.id,
                    args=keep_query(*invitation_parameters, state='new')
                ))
        return request.redirect(f"/calendar_booking/{booking.booking_token}/view?{keep_query(*invitation_parameters)}")

    def _get_extra_payment_form_values(self, **kwargs):
        """ Override of payment: additional rendering values for the payment page.
            This is used to give appointment specific values for rendering the page as well
            as custom landing and transaction routes. Template used is appointment_payment,
            see _get_payment_page_template_xmlid. See payment_pay in payment and
            account_payment modules for more information. """
        rendering_context_values = super()._get_extra_payment_form_values(**kwargs)
        appointment_type_id = self._cast_as_int(kwargs.get('appointment_type_id'))

        if not appointment_type_id:
            return rendering_context_values

        invoice_sudo = request.env['account.move'].sudo().browse(int(kwargs.get('invoice_id'))).exists()
        if not invoice_sudo or not invoice_sudo.calendar_booking_ids:
            raise NotFound()

        booking_sudo = invoice_sudo.calendar_booking_ids[0]
        appointment_type_sudo = booking_sudo.appointment_type_id
        if booking_sudo.calendar_event_id or not appointment_type_sudo or appointment_type_sudo.id != appointment_type_id:
            raise NotFound()

        filter_staff_user_ids = json.loads(unquote_plus(kwargs.get('filter_staff_user_ids') or '[]'))
        filter_resource_ids = json.loads(unquote_plus(kwargs.get('filter_resource_ids') or '[]'))
        users_possible = appointment_type_sudo.staff_user_ids.filtered(
            lambda user: user.id in filter_staff_user_ids
        ) if filter_staff_user_ids else appointment_type_sudo.staff_user_ids
        resources_possible = appointment_type_sudo.resource_ids.filtered(
            lambda user: user.id in filter_resource_ids
        ) if filter_resource_ids else appointment_type_sudo.resource_ids

        invitation_parameters = booking_sudo.appointment_invite_id._get_invitation_url_parameters()
        invoice_token = invoice_sudo._portal_ensure_token()
        rendering_context_values.update({
            'access_token': invoice_token,
            'appointment_type': appointment_type_sudo,
            'booking': booking_sudo,
            'cancel_booking_route': f"/calendar_booking/{booking_sudo.booking_token}/cancel?{keep_query(*invitation_parameters)}",
            'invoice_state': invoice_sudo.payment_state,
            'landing_route': "/appointment/{aid}/invoice/{inv_token}/post_payment?partner_id={pid}&{params}".format(
                aid=appointment_type_sudo.id,
                inv_token=invoice_token,
                pid=invoice_sudo.partner_id.id,
                params=keep_query(*invitation_parameters)
            ),
            'transaction_route': f'/invoice/transaction/{invoice_sudo.id}',
            'users_possible': users_possible,
            'resources_possible': resources_possible,
        })

        return rendering_context_values

    def _get_payment_page_template_xmlid(self, **kwargs):
        if kwargs.get('appointment_type_id'):
            return 'appointment_account_payment.appointment_payment'
        return super()._get_payment_page_template_xmlid(**kwargs)
