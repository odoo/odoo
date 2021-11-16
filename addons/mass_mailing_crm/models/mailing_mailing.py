# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _, tools


class MassMailing(models.Model):
    _name = 'mailing.mailing'
    _inherit = 'mailing.mailing'

    use_leads = fields.Boolean('Use Leads', compute='_compute_use_leads')
    crm_lead_count = fields.Integer('Leads/Opportunities Count', groups='sales_team.group_sale_salesman', compute='_compute_crm_lead_count')

    def _compute_use_leads(self):
        self.use_leads = self.env.user.has_group('crm.group_use_lead')

    def _compute_crm_lead_count(self):
        lead_data = self.env['crm.lead'].with_context(active_test=False).read_group(
            [('source_id', 'in', self.source_id.ids)],
            ['source_id'], ['source_id']
        )
        mapped_data = {datum['source_id'][0]: datum['source_id_count'] for datum in lead_data}
        for mass_mailing in self:
            mass_mailing.crm_lead_count = mapped_data.get(mass_mailing.source_id.id, 0)

    def action_redirect_to_leads_and_opportunities(self):
        view = 'crm.crm_lead_all_leads' if self.use_leads else 'crm.crm_lead_opportunities'
        action = self.env.ref(view).sudo().read()[0]
        action['view_mode'] = 'tree,kanban,graph,pivot,form,calendar'
        action['domain'] = [('source_id', 'in', self.source_id.ids)]
        action['context'] = {'active_test': False, 'create': False}
        return action

    def _prepare_statistics_email_values(self):
        self.ensure_one()
        values = super(MassMailing, self)._prepare_statistics_email_values()
        if not self.user_id:
            return values
        values['kpi_data'][1]['kpi_col1'] = {
            'value': tools.format_decimalized_number(self.crm_lead_count, decimal=0),
            'col_subtitle': _('LEADS'),
        }
        values['kpi_data'][1]['kpi_name'] = 'lead'
        return values
