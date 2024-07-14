# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, tools


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

        if not partner and self.partner_email:
            partner = self.env['res.partner'].search([('email_normalized', '=', tools.email_normalize(self.partner_email))], limit=1)

        if not partner and not email_only and self.partner_name:
            partner = self.env['res.partner'].search([('name', 'ilike', self.partner_name)], limit=1)

        if not partner and force_create:
            partner = self.env['res.partner'].create({
                'name': self.partner_name,
                'email': self.partner_email,
                'phone': self.partner_phone,
            })

        if partner and force_update:
            if not partner.email and self.partner_email:
                partner.email = self.partner_email
            if not partner.phone and self.partner_phone:
                partner.phone = self.partner_phone

        return partner
