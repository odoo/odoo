# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class CrmLeadForwardToPartner(models.TransientModel):
    """ Forward info history to partners. """
    _name = 'crm.lead.forward.to.partner'

    @api.model
    def default_get(self, fields):
        CrmLead = self.env['crm.lead']
        MailTemplate = self.env['mail.template']
        lead_template = self.env.ref('crm_partner_assign.email_template_lead_forward_mail', raise_if_not_found=False)
        res = super(CrmLeadForwardToPartner, self).default_get(fields)
        active_ids = self.env.context.get('active_ids')
        default_composition_mode = self.env.context.get('default_composition_mode')
        res['assignation_lines'] = []
        if lead_template:
            res['body'] = lead_template.body_html
        if active_ids:
            leads = CrmLead.browse(active_ids)
            if default_composition_mode == 'mass_mail':
                assigned_partners = leads.search_geo_partner()
            else:
                assigned_partners = {lead.id: lead.partner_assigned_id for lead in leads}
                res['partner_id'] = leads.mapped('partner_assigned_id').id
            for lead in leads:
                partner = assigned_partners.get(lead.id)
                res['assignation_lines'].append((0, 0, self._convert_to_assignation_line(lead, partner)))
        return res

    def _convert_to_assignation_line(self, lead, partner):
        lead_location = []
        partner_location = []
        if lead.country_id:
            lead_location.append(lead.country_id.name)
        if lead.city:
            lead_location.append(lead.city)
        if partner:
            if partner.country_id:
                partner_location.append(partner.country_id.name)
            if partner.city:
                partner_location.append(partner.city)
        return {'lead_id': lead.id,
                'lead_location': ", ".join(lead_location),
                'partner_assigned_id': partner and partner.id or False,
                'partner_location': ", ".join(partner_location),
                'lead_link': self.get_lead_portal_url(lead.id, lead.type),
                }
   
    @api.multi
    def action_forward(self):
        self.ensure_one()
        leads = CrmLead = self.env['crm.lead']
        MailTemplate = self.env['mail.template']
        lead_template = self.env.ref('crm_partner_assign.email_template_lead_forward_mail')
        portal_id = self.env.ref('base.group_portal').id
        local_context = self.env.context.copy()
        if not (self.forward_type == 'single'):
            no_email = set()
            for lead in self.assignation_lines:
                if lead.partner_assigned_id and not lead.partner_assigned_id.email:
                    no_email.add(lead.partner_assigned_id.name)
            if no_email:
                raise UserError(_('Set an email address for the partner(s): %s') % ", ".join(no_email))
        if self.forward_type == 'single' and not self.partner_id.email:
            raise UserError(_('Set an email address for the partner %s') % self.partner_id.name)

        partners_leads = {}
        for lead in self.assignation_lines:
            partner = self.forward_type == 'single' and self.partner_id or lead.partner_assigned_id
            lead_details = {
                'lead_link': lead.lead_link,
                'lead_id': lead.lead_id,
            }
            if partner:
                partner_leads = partners_leads.get(partner.id)
                if partner_leads:
                    partner_leads['leads'].append(lead_details)
                else:
                    partners_leads[partner.id] = {'partner': partner, 'leads': [lead_details]}
        stage = False
        if self.assignation_lines and self.assignation_lines[0].lead_id.type == 'lead':
            stage = self.env.ref('crm_partner_assign.stage_portal_lead_assigned', raise_if_not_found=False)
        for partner_id, partner_leads in partners_leads.items():
            in_portal = False
            for contact in (partner.child_ids or [partner]):
                if contact.user_ids:
                    in_portal = portal_id in [g.id for g in contact.user_ids[0].groups_id]

            local_context['partner_id'] = partner_leads['partner']
            local_context['partner_leads'] = partner_leads['leads']
            local_context['partner_in_portal'] = in_portal
            lead_template.with_context(local_context).send_mail(self.id)
            for lead in partner_leads['leads']:
                leads |= lead['lead_id']
            values = {'partner_assigned_id': partner_id, 'user_id': partner_leads['partner'].user_id.id}
            if stage:
                values['stage'] = stage.id
            leads.write(values)
            leads.message_subscribe([partner_id])
        return True

    def get_lead_portal_url(self, lead_id, type):
        action = type == 'opportunity' and 'action_portal_opportunities' or 'action_portal_leads'
        act = self.env.ref('crm_partner_assign.%s' % action, raise_if_not_found=False)
        portal_link = "%s/?db=%s#id=%s&action=%s&view_type=form" % (self.env['ir.config_parameter'].get_param('web.base.url'), self.env.cr.dbname, lead_id, (act and act.id or False))
        return portal_link

    def get_portal_url(self):
        portal_link = "%s/?db=%s" % (self.env['ir.config_parameter'].get_param('web.base.url'), self.env.cr.dbname)
        return portal_link
    forward_type = fields.Selection([
        ('single', 'a single partner: manual selection of partner'), 
        ('assigned', "several partners: automatic assignation, using GPS coordinates and partner's grades"), ], 
        string='Forward selected leads to',
        default=lambda self: self.env.context.get('forward_type') or 'single')
    partner_id = fields.Many2one('res.partner', string='Forward Leads To')
    assignation_lines = fields.One2many('crm.lead.assignation', 'forward_id', string='Partner Assignation')
    body = fields.Html(string='Contents', help='Automatically sanitized HTML contents')


class crm_lead_assignation (models.TransientModel):
    _name = 'crm.lead.assignation'
    forward_id = fields.Many2one('crm.lead.forward.to.partner', string='Partner Assignation')
    lead_id = fields.Many2one('crm.lead', string='Lead')
    lead_location = fields.Char(string='Lead Location')
    partner_assigned_id = fields.Many2one('res.partner', string='Assigned Partner')
    partner_location = fields.Char(string='Partner Location')
    lead_link = fields.Char(string='Lead  Single Links', size=2048)
    
    @api.onchange('lead_id')
    def on_change_lead_id(self):
        if not self.lead_id:
            self.lead_location = False
        lead = self.env['crm.lead'].browse(lead_id)
        lead_location = []
        if lead.country_id:
            lead_location.append(lead.country_id.name)
        if lead.city:
            lead_location.append(lead.city)
        self.lead_location = ", ".join(lead_location)

    @api.onchange('partner_assigned_id')
    def on_change_partner_assigned_id(self):
        if not self.partner_assigned_id:
            self.lead_location = False
        partner = self.env['res.partner'].browse(partner_assigned_id)
        if partner.country_id:
            partner_location.append(partner.country_id.name)
        if partner.city:
            partner_location.append(partner.city)
        self.partner_location = ", ".join(partner_location)
