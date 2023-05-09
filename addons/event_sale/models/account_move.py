# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from odoo import _, models

class AccountMove(models.Model):
    _inherit = 'account.move'

    def _invoice_paid_hook(self):
        """ When an invoice linked to a sales order selling registrations is
        paid confirm attendees. Attendees should indeed not be confirmed before
        full payment. Post tickets on paid orders too, accessible from portal."""
        res = super(AccountMove, self)._invoice_paid_hook()
        sale_order_line_ids = self.mapped('line_ids.sale_line_ids')
        sale_order_line_ids._update_registrations(confirm=True, mark_as_paid=True)

        RegistrationSudo = self.env['event.registration'].sudo()
        registrations_sudo = RegistrationSudo.search([('sale_order_line_id', 'in', sale_order_line_ids.ids)])
        registrations_per_order_event = defaultdict(lambda: defaultdict(lambda: self.env['event.registration']))
        for registration in registrations_sudo:
            registrations_per_order_event[registration.sale_order_id][registration.event_id] += registration

        for order, registrations_per_event in registrations_per_order_event.items():
            pdfs = []
            partner = order.partner_id
            for event in registrations_per_event:
                pdf = self.env['ir.actions.report'].sudo()._render_qweb_pdf('event.action_report_event_registration_full_page_ticket', registrations_per_event[event].ids)[0]
                pdfs += [(f'Tickets - {event.name}.pdf', pdf)]

            if pdfs:
                order.with_context(lang=partner.lang or self.env.user.lang).message_post(
                    partner_ids=[partner.id],
                    body=_('Please find attached the tickets linked to this sale order. You can also find them in the portal page of sale order %(sale_order_name)s.', sale_order_name=order.name),
                    attachments=pdfs,
                    subject=_('Your Event Tickets'),
                    subtype_xmlid='mail.mt_comment',
                    message_type='comment',
                )

        return res
