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
        self._raise_if_not_member_of('sales_team.group_sale_salesman')
        self._calculate_kpi('crm.lead', 'kpi_crm_lead_created_value')

    def _compute_kpi_crm_opportunities_won_value(self):
        self._raise_if_not_member_of('sales_team.group_sale_salesman')
        self._calculate_kpi(
            'crm.lead',
            'kpi_crm_opportunities_won_value',
            date_field='date_closed',
            additional_domain=[('type', '=', 'opportunity'), ('probability', '=', '100')],
        )

    def _get_kpi_custom_settings(self, company, user):
        res = super()._get_kpi_custom_settings(company, user)
        menu_id = self.env.ref('crm.crm_menu_root').id
        res['kpi_action']['kpi_crm_opportunities_won'] = f'crm.crm_lead_action_pipeline?menu_id={menu_id}'
        if user.has_group('crm.group_use_lead'):
            res['kpi_action']['kpi_crm_lead_created'] = f'crm.crm_lead_all_leads?menu_id={menu_id}'
        else:
            res['kpi_action']['kpi_crm_lead_created'] = f'crm.crm_lead_action_pipeline?menu_id={menu_id}'
        res['kpi_sequence']['kpi_crm_lead_created'] = 4550
        res['kpi_sequence']['kpi_crm_opportunities_won'] = 4555
        return res
