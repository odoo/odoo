# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import api, fields, models


class MassMailing(models.Model):
    _name = 'mail.mass_mailing'
    _inherit = 'mail.mass_mailing'

    crm_lead_activated = fields.Boolean('Use Leads', compute='_compute_crm_lead_activated')
    crm_lead_count = fields.Integer('Lead Count', compute='_compute_crm_lead_count')
    crm_opportunities_count = fields.Integer('Opportunities Count', compute='_compute_crm_opportunities_count')

    def _compute_crm_lead_activated(self):
        for mass_mailing in self:
            mass_mailing.crm_lead_activated = self.env.user.has_group('crm.group_use_lead')

    @api.depends('crm_lead_activated')
    def _compute_crm_lead_count(self):
        for mass_mailing in self:
            if mass_mailing.crm_lead_activated:
                mass_mailing.crm_lead_count = self.env['crm.lead'].search_count(self._get_crm_utm_domain())
            else:
                mass_mailing.crm_lead_count = 0

    @api.depends('crm_lead_activated')
    def _compute_crm_opportunities_count(self):
        for mass_mailing in self:
            if mass_mailing.crm_lead_activated:
                mass_mailing.crm_opportunities_count = 0
            else:
                mass_mailing.crm_opportunities_count = self.env['crm.lead'].search_count(self._get_crm_utm_domain())

    @api.multi
    def action_redirect_to_leads(self):
        action = self.env.ref('crm.crm_lead_all_leads').read()[0]
        action['domain'] = self._get_crm_utm_domain()
        action['context'] = {'default_type': 'lead'}
        return action

    @api.multi
    def action_redirect_to_opportunities(self):
        action = self.env.ref('crm.crm_lead_opportunities').read()[0]
        action['view_mode'] = 'tree,kanban,graph,pivot,form,calendar'
        action['domain'] = self._get_crm_utm_domain()
        return action

    def _get_crm_utm_domain(self):
        res = []
        if self.campaign_id:
            res.append(('campaign_id', '=', self.campaign_id.id))
        if self.source_id:
            res.append(('source_id', '=', self.source_id.id))
        if self.medium_id:
            res.append(('medium_id', '=', self.medium_id.id))
        if not res:
            res.append((0, '=', 1))
        return res
