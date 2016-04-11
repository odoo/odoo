# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class CrmConfiguration(models.TransientModel):
    _name = 'sale.config.settings'
    _inherit = ['sale.config.settings', 'fetchmail.config.settings']

    generate_sales_team_alias = fields.Boolean(
            string="Automatically generate an email alias at the sales team creation",
            help="Odoo will generate an email alias based on the sales team name")
    alias_prefix = fields.Char(string='Default Alias Name for Leads')
    alias_domain = fields.Char(string='Alias Domain', default=lambda self: self.env["ir.config_parameter"].get_param("mail.catchall.domain"))
    group_use_lead = fields.Selection([
            (0, "Each mail sent to the alias creates a new opportunity"),
            (1, "Use leads if you need a qualification step before creating an opportunity or a customer")
            ], string="Leads",
            implied_group='crm.group_use_lead')
    module_crm_voip = fields.Boolean(string="VoIP integration", help="Integration with Asterisk")
    module_website_sign = fields.Boolean(string="Odoo Sign")

    def _find_default_lead_alias_id(self):
        alias = self.env.ref('crm.mail_alias_lead_info', False)
        if not alias:
            alias = self.env['mail.alias'].search(
                [
                    ('alias_model_id.model', '=', 'crm.lead'),
                    ('alias_force_thread_id', '=', False),
                    ('alias_parent_model_id.model', '=', 'crm.team'),
                    ('alias_parent_thread_id', '=', False),
                    ('alias_defaults', '=', '{}')
                ], limit=1)
        return alias.id

    @api.model
    def get_default_generate_sales_team_alias(self, fields):
        return {'generate_sales_team_alias': self.env['ir.values'].get_default(
            'sales.config.settings', 'generate_sales_team_alias')}

    @api.multi
    def set_default_generate_sales_team_alias(self):
        self.ensure_one()
        IrValues = self.env['ir.values']
        IrValues = IrValues.sudo() if self.user_has_groups('base.group_configuration') else IrValues
        IrValues.set_default('sales.config.settings', 'generate_sales_team_alias', self.generate_sales_team_alias)

    @api.model
    def get_default_alias_prefix(self, fields):
        alias_id = self._find_default_lead_alias_id()
        alias_name = self.env['mail.alias'].browse(alias_id).alias_name
        return {'alias_prefix': alias_name}

    @api.multi
    def set_default_alias_prefix(self):
        MailAlias = self.env['mail.alias']
        for record in self:
            alias_id = self._find_default_lead_alias_id()
            if not alias_id:
                MailAlias.with_context(alias_model_name='crm.lead', alias_parent_model_name='crm.team').create(
                    {'alias_name': record.alias_prefix})
            else:
                MailAlias.browse(alias_id).write({'alias_name': record.alias_prefix})
        return True
