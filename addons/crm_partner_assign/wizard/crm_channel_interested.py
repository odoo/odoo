# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class CrmLeadForwardToPartner(models.TransientModel):
    """ Forward info history to partners. """
    _name = 'crm.lead.channel.interested'

    interested = fields.Boolean(string='Interested by this lead', default=lambda self: self.env.context.get('interested', True))
    contacted = fields.Boolean(string='Did you contact the lead?', help="The lead has been contacted")
    comment = fields.Text(help="What are the elements that have led to this decision?", required=True)

    @api.multi
    def action_confirm(self):
        self.ensure_one()
        if self.interested and not self.contacted:
            raise UserError(_("You must contact the lead before saying that you are interested"))
        CrmLead = self.env['crm.lead']
        CrmLead.check_access_rights('write')
        leads = CrmLead.browse(self.env.context.get('active_ids', []))
        if self.interested:
            message = _('<p>I am interested by this lead.</p>')
            values = {}
        else:
            stage = 'stage_portal_lead_recycle'
            if self.contacted:
                message = _('<p>I am not interested by this lead. I contacted the lead.</p>')
            else:
                message = _('<p>I am not interested by this lead. I have not contacted the lead.</p>')
            values = {'partner_assigned_id': False}
            partners = self.env['res.partner'].sudo().search([('id', 'child_of', self.env.user.partner_id.commercial_partner_id.id)])
            leads.sudo().message_unsubscribe(partners.ids)
            stage_id = self.env.ref("crm_partner_assign.%s" % (stage), raise_if_not_found =False)
            if stage_id:
                values.update({'stage_id': stage_id.id})
        if self.comment:
            message += '<p>%s</p>' % self.comment
        for lead in leads:
            lead.message_post(body=message, subtype="mail.mt_comment")
        if values:
            leads.sudo().write(values)
        if self.interested:
            for lead in leads:
                lead.sudo().convert_opportunity(lead.partner_id and lead.partner_id.id or None)
        return {
            'type': 'ir.actions.act_window_close',
        }
