# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, tools, _


class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    def _find_matching_partner(self, email_only=False, force_create=False, force_update=True):
        """ Try to find a matching partner with available information on the
        ticket, using notably customer's name, email, phone, ...

        # TODO : Move this + the one from crm into mail_thread

        :return: partner browse record
        """
        self.ensure_one()
        partner = self.partner_id

        if not partner and self.email_cc:
            partner = self.env['res.partner'].search([('email_normalized', '=', tools.email_normalize(self.email_cc))], limit=1)
        elif self.partner_phone:
            partner = self.env['res.partner'].search([('phone', '=', self.partner_phone)], limit=1)

        if not partner and force_create:
            partner = self.env['res.partner'].create({
                'name': self.partner_name or self.name,
                'email': self.partner_name or self.email_cc,
                'phone': self.partner_phone,
            })

        if partner and force_update:
            if not partner.email and self.partner_email:
                partner.email = self.partner_email
            if not partner.phone and self.partner_phone:
                partner.phone = self.partner_phone

        return partner

    def action_convert_ticket_to_lead_or_opportunity(self):
        return {
            'name': _('Convert to Lead') if self.env.user.has_group('crm.group_use_lead') else _('Convert to Opportunity'),
            'type': 'ir.actions.act_window',
            'res_model': 'helpdesk.ticket.to.lead',
            'view_mode': 'form',
            'view_id': self.env.ref('crm_helpdesk.helpdesk_ticket_to_lead_view_form').id,
            'target': 'new',
            'context': {
                'dialog_size': 'medium',
            },
        }
