# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    group_use_lead = fields.Boolean(string="Leads", implied_group='crm.group_use_lead')
    group_use_recurring_revenues = fields.Boolean(string="Recurring Revenues", implied_group='crm.group_use_recurring_revenues')
    module_crm_iap_lead = fields.Boolean("Generate new leads based on their country, industries, size, etc.")
    module_crm_iap_lead_website = fields.Boolean("Create Leads/Opportunities from your website's traffic")
    module_crm_iap_lead_enrich = fields.Boolean("Enrich your leads automatically with company data based on their email address.")
    module_mail_client_extension = fields.Boolean("See and manage users, companies, and leads from our mail client extensions.")
    lead_enrich_auto = fields.Selection([
        ('manual', 'Enrich leads on demand only'),
        ('auto', 'Enrich all leads automatically'),
    ], string='Enrich lead automatically', default='manual', config_parameter='crm.iap.lead.enrich.setting')
    lead_mining_in_pipeline = fields.Boolean("Create a lead mining request directly from the opportunity pipeline.", config_parameter='crm.lead_mining_in_pipeline')
    predictive_lead_scoring_start_date = fields.Date(string='Lead Scoring Starting Date', compute="_compute_pls_start_date", inverse="_inverse_pls_start_date_str")
    predictive_lead_scoring_start_date_str = fields.Char(string='Lead Scoring Starting Date in String', config_parameter='crm.pls_start_date')
    predictive_lead_scoring_fields = fields.Many2many('crm.lead.scoring.frequency.field', string='Lead Scoring Frequency Fields', compute="_compute_pls_fields", inverse="_inverse_pls_fields_str")
    predictive_lead_scoring_fields_str = fields.Char(string='Lead Scoring Frequency Fields in String', config_parameter='crm.pls_fields')

    @api.depends('predictive_lead_scoring_fields_str')
    def _compute_pls_fields(self):
        """ As config_parameters does not accept m2m field,
            we get the fields back from the Char config field, to ease the configuration in config panel """
        for setting in self:
            if setting.predictive_lead_scoring_fields_str:
                names = setting.predictive_lead_scoring_fields_str.split(',')
                fields = self.env['ir.model.fields'].search([('name', 'in', names), ('model', '=', 'crm.lead')])
                setting.predictive_lead_scoring_fields = self.env['crm.lead.scoring.frequency.field'].search([('field_id', 'in', fields.ids)])
            else:
                setting.predictive_lead_scoring_fields = None

    def _inverse_pls_fields_str(self):
        """ As config_parameters does not accept m2m field,
            we store the fields with a comma separated string into a Char config field """
        for setting in self:
            if setting.predictive_lead_scoring_fields:
                setting.predictive_lead_scoring_fields_str = ','.join(setting.predictive_lead_scoring_fields.mapped('field_id.name'))
            else:
                setting.predictive_lead_scoring_fields_str = ''

    @api.depends('predictive_lead_scoring_start_date_str')
    def _compute_pls_start_date(self):
        """ As config_parameters does not accept Date field,
            we get the date back from the Char config field, to ease the configuration in config panel """
        for setting in self:
            setting.predictive_lead_scoring_start_date = fields.Date.to_date(setting.predictive_lead_scoring_start_date_str)

    def _inverse_pls_start_date_str(self):
        """ As config_parameters does not accept Date field,
            we store the date formated string into a Char config field """
        for setting in self:
            if setting.predictive_lead_scoring_start_date:
                setting.predictive_lead_scoring_start_date_str = fields.Date.to_string(setting.predictive_lead_scoring_start_date)

    def set_values(self):
        group_lead_before = self.env.ref('crm.group_use_lead') in self.env.user.groups_id
        super(ResConfigSettings, self).set_values()
        group_lead_after = self.env.ref('crm.group_use_lead') in self.env.user.groups_id
        if group_lead_before != group_lead_after:
            teams = self.env['crm.team'].search([])
            teams.filtered('use_opportunities').use_leads = group_lead_after
            for team in teams:
                team.alias_id.write(team._alias_get_creation_values())

    # ACTIONS
    def action_reset_lead_probabilities(self):
        if self.env.user._is_admin():
            self.env['crm.lead'].sudo()._cron_update_automated_probabilities()
