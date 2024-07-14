# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class CrmLeadConvert2Ticket(models.TransientModel):
    """ wizard to convert a Lead into a Helpdesk ticket and move the Mail Thread """
    _name = "crm.lead.convert2ticket"
    _description = 'Lead convert to Ticket'

    @api.model
    def default_get(self, fields):
        result = super(CrmLeadConvert2Ticket, self).default_get(fields)
        if 'partner_id' in fields:
            lead_id = result.get('lead_id')
            if lead_id:
                lead = self.env['crm.lead'].browse(lead_id)
                result['partner_id'] = lead._find_matching_partner().id
        if 'team_id' in fields:
            team_ids = self.env['helpdesk.team'].search([], limit=2)
            result['team_id'] = team_ids[0].id if len(team_ids) == 1 else None
        return result

    lead_id = fields.Many2one(
        'crm.lead', string='Lead', domain=[('type', '=', 'lead')],
        default=lambda self: self.env.context.get('active_id', None),
    )
    partner_id = fields.Many2one('res.partner', 'Customer')
    team_id = fields.Many2one('helpdesk.team', string='Team', required=True)
    ticket_type_id = fields.Many2one('helpdesk.ticket.type', "Ticket Type")

    def action_lead_to_helpdesk_ticket(self):
        self.ensure_one()
        # get the lead to transform
        lead = self.lead_id
        partner = self.partner_id
        if not partner and (lead.partner_name or lead.contact_name):
            lead._handle_partner_assignment(create_missing=True)
            partner = lead.partner_id

        # prepare new helpdesk.ticket values
        vals = {
            "name": lead.name,
            "description": lead.description,
            "team_id": self.team_id.id,
            "ticket_type_id": self.ticket_type_id.id,
            "partner_id": partner.id,
            "user_id": None,
            "campaign_id": lead.campaign_id.id,
            "medium_id": lead.medium_id.id,
            "source_id": lead.source_id.id,
        }
        if lead.contact_name:
            vals["partner_name"] = lead.contact_name
        if lead.phone:  # lead phone is always sync with partner phone
            vals["partner_phone"] = lead.phone
        else:  # if partner is not on lead -> take partner phone first
            vals["partner_phone"] = partner.phone or lead.mobile or partner.mobile
        if lead.email_from:
            vals['partner_email'] = lead.email_from

        # create and add a specific creation message
        ticket_sudo = self.env['helpdesk.ticket'].with_context(
            mail_create_nosubscribe=True, mail_create_nolog=True
        ).sudo().create(vals)
        ticket_sudo.message_post_with_source(
            'mail.message_origin_link',
            render_values={'self': ticket_sudo, 'origin': lead},
            subtype_xmlid='mail.mt_note',
        )

        # move the mail thread
        lead.message_change_thread(ticket_sudo)
        # move attachments
        attachments = self.env['ir.attachment'].search([('res_model', '=', 'crm.lead'), ('res_id', '=', lead.id)])
        attachments.sudo().write({'res_model': 'helpdesk.ticket', 'res_id': ticket_sudo.id})
        # archive the lead
        lead.action_archive()

        # return to ticket (if can see) or lead (if cannot)
        try:
            self.env['helpdesk.ticket'].browse(ticket_sudo.ids).check_access_rule('read')
        except:
            return {
                'name': _('Lead Converted'),
                'view_mode': 'form',
                'res_model': lead._name,
                'type': 'ir.actions.act_window',
                'res_id': lead.id
            }

        # return the action to go to the form view of the new Ticket
        view = self.env.ref('helpdesk.helpdesk_ticket_view_form')
        return {
            'name': _('Ticket created'),
            'view_mode': 'form',
            'view_id': view.id,
            'res_model': 'helpdesk.ticket',
            'type': 'ir.actions.act_window',
            'res_id': ticket_sudo.id,
            'context': self.env.context
        }
