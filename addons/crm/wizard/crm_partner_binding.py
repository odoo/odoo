# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PartnerBinding(models.TransientModel):
    """
        Handle the partner binding or generation in any CRM wizard that requires
        such feature, like the lead2opportunity wizard, or the
        phonecall2opportunity wizard.  Try to find a matching partner from the
        CRM model's information (name, email, phone number, etc) or create a new
        one on the fly.
        Use it like a mixin with the wizard of your choice.
    """

    _name = 'crm.partner.binding'
    _description = 'Partner linking/binding in CRM wizard'

    @api.model
    def default_get(self, fields):
        res = super(PartnerBinding, self).default_get(fields)
        partner_id = self._find_matching_partner()

        if 'action' in fields and not res.get('action'):
            res['action'] = 'exist' if partner_id else 'create'
        if 'partner_id' in fields:
            res['partner_id'] = partner_id
        return res

    action = fields.Selection([
        ('exist', 'Link to an existing customer'),
        ('create', 'Create a new customer'),
        ('nothing', 'Do not link to a customer')
    ], 'Related Customer', required=True)
    partner_id = fields.Many2one('res.partner', 'Customer')

    @api.model
    def _find_matching_partner(self):
        """ Try to find a matching partner regarding the active model data, like
            the customer's name, email, phone number, etc.
            :return int partner_id if any, False otherwise
        """
        # active model has to be a lead
        if self._context.get('active_model') != 'crm.lead' or not self._context.get('active_id'):
            return False

        lead = self.env['crm.lead'].browse(self._context.get('active_id'))

        # find the best matching partner for the active model
        Partner = self.env['res.partner']
        if lead.partner_id:  # a partner is set already
            return lead.partner_id.id

        if lead.email_from:  # search through the existing partners based on the lead's email
            partner = Partner.search([('email', '=', lead.email_from)], limit=1)
            return partner.id

        if lead.partner_name:  # search through the existing partners based on the lead's partner or contact name
            partner = Partner.search([('name', 'ilike', '%' + lead.partner_name + '%')], limit=1)
            return partner.id

        if lead.contact_name:
            partner = Partner.search([('name', 'ilike', '%' + lead.contact_name+'%')], limit=1)
            return partner.id

        return False
