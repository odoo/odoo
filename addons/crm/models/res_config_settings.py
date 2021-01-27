# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    crm_alias_prefix = fields.Char(
        'Default Alias Name for Leads',
        compute="_compute_crm_alias_prefix" , readonly=False, store=True)
    generate_lead_from_alias = fields.Boolean(
        'Manual Assignment of Emails', config_parameter='crm.generate_lead_from_alias',
        compute="_compute_generate_lead_from_alias", readonly=False, store=True)
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

    def _find_default_lead_alias_id(self):
        alias = self.env.ref('crm.mail_alias_lead_info', False)
        if not alias:
            alias = self.env['mail.alias'].search([
                ('alias_model_id.model', '=', 'crm.lead'),
                ('alias_force_thread_id', '=', False),
                ('alias_parent_model_id.model', '=', 'crm.team'),
                ('alias_parent_thread_id', '=', False),
                ('alias_defaults', '=', '{}')
            ], limit=1)
        return alias

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
            lead_scoring_start_date = setting.predictive_lead_scoring_start_date_str
            # if config param is deleted / empty, set the date 8 days prior to current date
            if not lead_scoring_start_date:
                setting.predictive_lead_scoring_start_date = fields.Date.to_date(fields.Date.today() - timedelta(days=8))
            else:
                try:
                    setting.predictive_lead_scoring_start_date = fields.Date.to_date(lead_scoring_start_date)
                except ValueError:
                    # the config parameter is malformed, so set the date 8 days prior to current date
                    setting.predictive_lead_scoring_start_date = fields.Date.to_date(fields.Date.today() - timedelta(days=8))

    def _inverse_pls_start_date_str(self):
        """ As config_parameters does not accept Date field,
            we store the date formated string into a Char config field """
        for setting in self:
            if setting.predictive_lead_scoring_start_date:
                setting.predictive_lead_scoring_start_date_str = fields.Date.to_string(setting.predictive_lead_scoring_start_date)

    @api.depends('group_use_lead')
    def _compute_generate_lead_from_alias(self):
        """ Reset alias / leads configuration if leads are not used """
        for setting in self.filtered(lambda r: not r.group_use_lead):
            setting.generate_lead_from_alias = False

    @api.depends('generate_lead_from_alias')
    def _compute_crm_alias_prefix(self):
        for setting in self:
            setting.crm_alias_prefix = (setting.crm_alias_prefix or 'contact') if setting.generate_lead_from_alias else False

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        alias = self._find_default_lead_alias_id()
        res.update(
            crm_alias_prefix=alias.alias_name if alias else False,
        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        alias = self._find_default_lead_alias_id()
        if alias:
            alias.write({'alias_name': self.crm_alias_prefix})
        else:
            self.env['mail.alias'].create({
                'alias_name': self.crm_alias_prefix,
                'alias_model_id': self.env['ir.model']._get('crm.lead').id,
                'alias_parent_model_id': self.env['ir.model']._get('crm.team').id,
            })
        for team in self.env['crm.team'].search([]):
            team.alias_id.write(team._alias_get_creation_values())

    # ACTIONS
    def action_reset_lead_probabilities(self):
        if self.env.user._is_admin():
            self.env['crm.lead'].sudo()._cron_update_automated_probabilities()
