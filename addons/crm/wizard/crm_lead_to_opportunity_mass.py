# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class Lead2OpportunityMassConvert(models.TransientModel):

    _name = 'crm.lead2opportunity.partner.mass'
    _description = 'Convert Lead to Opportunity (in mass)'
    _inherit = 'crm.lead2opportunity.partner'

    @api.model
    def default_get(self, fields):
        res = super(Lead2OpportunityMassConvert, self).default_get(fields)
        if 'partner_id' in fields:  # avoid forcing the partner of the first lead as default
            res['partner_id'] = False
        if 'action' in fields:
            res['action'] = 'each_exist_or_create'
        if 'name' in fields:
            res['name'] = 'convert'
        if 'opportunity_ids' in fields:
            res['opportunity_ids'] = False
        return res

    user_ids = fields.Many2many('res.users', string='Salesmen')
    team_id = fields.Many2one('crm.team', 'Sales Team', index=True)
    deduplicate = fields.Boolean('Apply deduplication', default=True, help='Merge with existing leads/opportunities of each partner')
    action = fields.Selection(selection_add=[
        ('each_exist_or_create', 'Use existing partner or create'),
        ('nothing', 'Do not link to a customer')
    ], string='Related Customer', required=True)
    force_assignation = fields.Boolean('Force assignation', help='If unchecked, this will leave the salesman of duplicated opportunities')

    @api.onchange('action')
    def _onchange_action(self):
        if self.action != 'exist':
            self.partner_id = False

    @api.onchange('deduplicate')
    def _onchange_deduplicate(self):
        active_leads = self.env['crm.lead'].browse(self._context['active_ids'])
        partner_ids = [(lead.partner_id.id, lead.partner_id and lead.partner_id.email or lead.email_from) for lead in active_leads]
        partners_duplicated_leads = {}
        for partner_id, email in partner_ids:
            duplicated_leads = self._get_duplicated_leads(partner_id, email)
            if len(duplicated_leads) > 1:
                partners_duplicated_leads.setdefault((partner_id, email), []).extend(duplicated_leads)

        leads_with_duplicates = []
        for lead in active_leads:
            lead_tuple = (lead.partner_id.id, lead.partner_id.email if lead.partner_id else lead.email_from)
            if len(partners_duplicated_leads.get(lead_tuple, [])) > 1:
                leads_with_duplicates.append(lead.id)

        self.opportunity_ids = self.env['crm.lead'].browse(leads_with_duplicates)

    def _convert_opportunity(self, vals):
        """ When "massively" (more than one at a time) converting leads to
            opportunities, check the salesteam_id and salesmen_ids and update
            the values before calling super.
        """
        self.ensure_one()
        salesteam_id = self.team_id.id if self.team_id else False
        salesmen_ids = []
        if self.user_ids:
            salesmen_ids = self.user_ids.ids
        vals.update({'user_ids': salesmen_ids, 'team_id': salesteam_id})
        return super(Lead2OpportunityMassConvert, self)._convert_opportunity(vals)

    def mass_convert(self):
        self.ensure_one()
        if self.name == 'convert' and self.deduplicate:
            merged_lead_ids = set()
            remaining_lead_ids = set()
            lead_selected = self._context.get('active_ids', [])
            for lead_id in lead_selected:
                if lead_id not in merged_lead_ids:
                    lead = self.env['crm.lead'].browse(lead_id)
                    duplicated_leads = self._get_duplicated_leads(lead.partner_id.id, lead.partner_id.email if lead.partner_id else lead.email_from)
                    if len(duplicated_leads) > 1:
                        lead = duplicated_leads.merge_opportunity()
                        merged_lead_ids.update(duplicated_leads.ids)
                        remaining_lead_ids.add(lead.id)
            active_ids = set(self._context.get('active_ids', {}))
            active_ids = (active_ids - merged_lead_ids) | remaining_lead_ids

            self = self.with_context(active_ids=list(active_ids))  # only update active_ids when there are set
        no_force_assignation = self._context.get('no_force_assignation', not self.force_assignation)
        return self.with_context(no_force_assignation=no_force_assignation).action_apply()
