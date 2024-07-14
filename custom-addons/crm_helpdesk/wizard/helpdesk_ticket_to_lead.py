# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HelpdeskTicketConvert2Lead(models.TransientModel):
    _name = "helpdesk.ticket.to.lead"
    _description = "Convert Ticket to Lead"

    @api.model
    def default_get(self, fields):
        res = super(HelpdeskTicketConvert2Lead, self).default_get(fields)

        if not res.get('ticket_id') and self.env.context.get('active_id'):
            res['ticket_id'] = self.env.context['active_id']
        if res.get('ticket_id'):
            ticket = self.env['helpdesk.ticket'].browse(res.get('ticket_id'))
            if not ticket.active:
                raise ValidationError(_('The archived ticket can not converted as lead.'))
        return res

    ticket_id = fields.Many2one('helpdesk.ticket', required=True, readonly=False)
    action = fields.Selection([
        ('create', 'Create a new customer'),
        ('exist', 'Link to an existing customer'),
        ('nothing', 'Do not link to a customer')
    ], string='Related Customer', compute='_compute_action', readonly=False, store=True)
    partner_id = fields.Many2one('res.partner', string="Customer", compute='_compute_partner_id', store=True, readonly=False)
    team_id = fields.Many2one('crm.team', string="Sales Team", compute='_compute_team_id', store=True, readonly=False)
    user_id = fields.Many2one('res.users', string="Salesperson", compute='_compute_user_id', store=True, readonly=False)

    @api.depends('ticket_id')
    def _compute_action(self):
        for convert in self:
            if not convert.ticket_id:
                convert.action = 'nothing'
            else:
                partner = convert.ticket_id._find_matching_partner()
                if partner:
                    convert.action = 'exist'
                elif convert.ticket_id.partner_name:
                    convert.action = 'create'
                else:
                    convert.action = 'nothing'

    @api.depends('action', 'ticket_id')
    def _compute_partner_id(self):
        for convert in self:
            if convert.action == 'exist':
                convert.partner_id = convert.ticket_id._find_matching_partner()
            else:
                convert.partner_id = False

    @api.depends('ticket_id.user_id', 'user_id')
    def _compute_team_id(self):
        """ First, team id is chosen, then, user. If user from ticket have a
        team_id, use this user and their team."""
        for convert in self:
            user = convert.user_id or convert.ticket_id.user_id
            if not user or (convert.team_id and user in convert.team_id.member_ids | convert.team_id.user_id):
                continue
            team = self.env['crm.team']._get_default_team_id(user_id=user.id, domain=None)
            convert.team_id = team.id

    @api.depends('ticket_id', 'team_id')
    def _compute_user_id(self):
        for convert in self:
            user = convert.ticket_id.user_id
            convert.user_id = user if user and user in convert.team_id.member_ids else False

    def action_convert_to_lead(self):
        self.ensure_one()
        # create partner if needed
        if self.action == 'create':
            self.partner_id = self.ticket_id._find_matching_partner(force_create=True).id

        lead_sudo = self.env['crm.lead'].with_context(
            mail_create_nosubscribe=True,
            mail_create_nolog=True
        ).sudo().create({
            'name': self.ticket_id.name,
            'partner_id': self.partner_id.id,
            'team_id': self.team_id.id,
            'user_id': self.user_id.id,
            'description': self.ticket_id.description,
            'email_cc': self.ticket_id.email_cc,
            "campaign_id": self.ticket_id.campaign_id.id,
            "medium_id": self.ticket_id.medium_id.id,
            "source_id": self.ticket_id.source_id.id,
        })
        ticket_link = self.ticket_id._get_html_link(title=self.ticket_id.name +' #({})'.format(self.ticket_id.id))
        lead_sudo.message_post(
            body=_('This lead has been created from ticket: %s', ticket_link),
            message_type='comment',
            subtype_xmlid='mail.mt_note',
        )

        # move the mail thread and attachments
        self.ticket_id.message_change_thread(lead_sudo)
        attachments = self.env['ir.attachment'].search([('res_model', '=', 'helpdesk.ticket'), ('res_id', '=', self.ticket_id.id)])
        attachments.sudo().write({'res_model': 'crm.lead', 'res_id': lead_sudo.id})
        self.ticket_id.action_archive()

        # After mail thread move, add linked lead message to ticket
        self.ticket_id.message_post_with_source(
            'helpdesk.ticket_conversion_link',
            render_values={'created_record': lead_sudo, 'message': _('Lead created')},
            subtype_xmlid='mail.mt_note',
        )

        # return to lead (if can see) or ticket (if cannot)
        try:
            self.env['crm.lead'].check_access_rights('read')
            self.env['crm.lead'].browse(lead_sudo.ids).check_access_rule('read')
        except:
            return {
                'name': _('Ticket Converted'),
                'view_mode': 'form',
                'res_model': self.ticket_id._name,
                'type': 'ir.actions.act_window',
                'res_id': self.ticket_id.id
            }

        # return the action to go to the form view of the new Ticket
        action = self.sudo().env.ref('crm.crm_lead_all_leads').read()[0]
        action.update({
            'res_id': lead_sudo.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
        })
        return action
