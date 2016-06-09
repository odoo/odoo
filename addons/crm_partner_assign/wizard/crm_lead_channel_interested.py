# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class CrmLeadForwardToPartner(models.TransientModel):
    """ Forward info history to partners. """
    _name = 'crm.lead.channel.interested'

    interested = fields.Boolean(string='Interested by this lead', default=lambda self: self._context.get('interested', True))
    contacted = fields.Boolean(string='Did you contact the lead?', help="The lead has been contacted")
    comment = fields.Text(string='Comment', required=True, help="What are the elements that have led to this decision?")

    @api.multi
    def action_confirm(self):
        self.ensure_one()
        if self.interested and not self.contacted:
            raise UserError(_("You must contact the lead before saying that you are interested"))
        Lead = self.env['crm.lead']
        leads = Lead.browse(context.get('active_ids', []))
        Lead.check_access_rights('write')
        if self.interested:
            message = _('<p>I am interested by this lead.</p>')
            values = {}
        else:
            if self.contacted:
                message = _('<p>I am not interested by this lead. I contacted the lead.</p>')
            else:
                message = _('<p>I am not interested by this lead. I have not contacted the lead.</p>')
            values = {'partner_assigned_id': False}
            commercial_partner_id = self.env.user.partner_id.commercial_partner_id.id
            partner_ids = self.env['res.partner'].sudo().search([('id', 'child_of', commercial_partner_id)]).ids
            leads.sudo().with_context({}).message_unsubscribe(partner_ids)
        if self.comment:
            message += '<p>%s</p>' % self.comment
        for lead in leads:
            lead.message_post(body=message, subtype="mail.mt_note")
        if values:
            leads.sudo().write(values)
            leads.sudo().set_tag_assign(False)
        if self.interested:
            for lead in leads:
                lead.sudo().convert_opportunity(lead.partner_id.id)
        return {
            'type': 'ir.actions.act_window_close',
        }
