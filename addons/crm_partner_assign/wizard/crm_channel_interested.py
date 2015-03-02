# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models, _
from openerp.exceptions import UserError


class CrmLeadForwardToPartner(models.TransientModel):
    """ Forward info history to partners. """
    _name = 'crm.lead.channel.interested'

    interested = fields.Boolean(string='Interested by this lead',
                                default=lambda self: self.env.context.get('interested', True))
    contacted = fields.Boolean(string='Did you contact the lead?',
                               help="The lead has been contacted")
    comment = fields.Text(help="What are the elements that have led to this decision?",
                          required=True)

    @api.multi
    def action_confirm(self):
        if self.interested and not self.contacted:
            raise UserError(_("You must contact the lead before saying that you are interested"))
        CrmLead = self.env['crm.lead']
        CrmLead.check_access_rights('write')
        if self.interested:
            message = _('<p>I am interested by this lead.</p>')
            values = {}
        else:
            stage = 'stage_portal_lead_recycle'
            message = _('<p>I am not interested by this lead. I %scontacted the lead.</p>') % (not self.contacted and 'have not ' or '')
            values = {'partner_assigned_id': False}
            partners = self.env['res.partner'].sudo().search([
                ('id', 'child_of', self.env.user.partner_id.commercial_partner_id.id)])
            CrmLead.sudo().browse(self.env.context.get('active_ids', [])).message_unsubscribe(partners.ids)
            try:
                stage_id = self.env.ref("crm_partner_assign.%s" % (stage)).id
            except ValueError:
                stage_id = False
            if stage_id:
                values.update({'stage_id': stage_id})
        if self.comment:
            message += '<p>%s</p>' % self.comment
        for active_id in self.env.context.get('active_ids', []):
            CrmLead.browse(active_id).message_post(body=message, subtype="mail.mt_comment")
        if values:
            CrmLead.sudo().browse(self.env.context.get('active_ids', [])).write(values)
        if self.interested:
            for lead in CrmLead.browse(self.env.context.get('active_ids', [])):
                CrmLead.sudo().browse(lead.id).convert_opportunity(lead.partner_id and lead.partner_id.id or None)
        return {
            'type': 'ir.actions.act_window_close',
        }
