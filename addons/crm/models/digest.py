# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import AccessError


class DigestDigest(models.Model):
    _inherit = 'digest.digest'

    kpi_crm_lead_created = fields.Boolean('New Leads')
    kpi_crm_lead_created_value = fields.Integer(compute='_compute_kpi_crm_lead_created_value')
    kpi_crm_opportunities_won = fields.Boolean('Opportunities Won')
    kpi_crm_opportunities_won_value = fields.Integer(compute='_compute_kpi_crm_opportunities_won_value')

    def _compute_kpi_crm_lead_created_value(self):
        if not self.env.user.has_group('sales_team.group_sale_salesman'):
            raise AccessError(_("Do not have access, skip this data for user's digest email"))

        self._calculate_company_based_kpi('crm.lead', 'kpi_crm_lead_created_value')

    def _compute_kpi_crm_opportunities_won_value(self):
        if not self.env.user.has_group('sales_team.group_sale_salesman'):
            raise AccessError(_("Do not have access, skip this data for user's digest email"))

        self._calculate_company_based_kpi(
            'crm.lead',
            'kpi_crm_opportunities_won_value',
            date_field='date_closed',
            additional_domain=[('type', '=', 'opportunity'), ('probability', '=', '100')],
        )

    def _compute_kpis_actions(self, company, user):
        res = super()._compute_kpis_actions(company, user)
        res['kpi_crm_lead_created'] = 'crm.crm_lead_action_pipeline?menu_id=%s' % self.env.ref('crm.crm_menu_root').id
        res['kpi_crm_opportunities_won'] = 'crm.crm_lead_action_pipeline?menu_id=%s' % self.env.ref('crm.crm_menu_root').id
        if user.has_group('crm.group_use_lead'):
            res['kpi_crm_lead_created'] = 'crm.crm_lead_all_leads?menu_id=%s' % self.env.ref('crm.crm_menu_root').id
        return res
