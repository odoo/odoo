# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class Opportunity2Quotation(models.TransientModel):
    _name = 'crm.quotation.partner'
    _description = 'Create new or use existing Customer on new Quotation'

    @api.model
    def default_get(self, fields):
        result = super(Opportunity2Quotation, self).default_get(fields)

        active_model = self._context.get('active_model')
        if active_model != 'crm.lead':
            raise UserError(_('You can only apply this action from a lead.'))

        lead = False
        if result.get('lead_id'):
            lead = self.env['crm.lead'].browse(result['lead_id'])
        elif 'lead_id' in fields and self._context.get('active_id'):
            lead = self.env['crm.lead'].browse(self._context['active_id'])
        if lead:
            result['lead_id'] = lead.id
            partner_id = result.get('partner_id') or lead._find_matching_partner()
            if 'action' in fields and not result.get('action'):
                result['action'] = 'exist' if partner_id else 'create'
            if 'partner_id' in fields and not result.get('partner_id'):
                result['partner_id'] = partner_id

        return result

    action = fields.Selection([
        ('create', 'Create a new customer'),
        ('exist', 'Link to an existing customer'),
        ('nothing', 'Do not link to a customer')
    ], string='Quotation Customer', required=True)
    lead_id = fields.Many2one('crm.lead', "Associated Lead", required=True)
    partner_id = fields.Many2one('res.partner', 'Customer')

    def action_apply(self):
        """ Convert lead to opportunity or merge lead and opportunity and open
            the freshly created opportunity view.
        """
        self.ensure_one()
        if self.action != 'nothing':
            self.lead_id.write({
                'partner_id': self.partner_id.id if self.action == 'exist' else self._create_partner()
            })
            self.lead_id._onchange_partner_id()
        return self.lead_id.action_new_quotation()

    def _create_partner(self):
        """ Create partner based on action.
            :return int: created res.partner id
        """
        self.ensure_one()
        result = self.lead_id.handle_partner_assignation(action='create')
        return result.get(self.lead_id.id)
