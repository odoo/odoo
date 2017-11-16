# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    crm_alias_prefix = fields.Char('Default Alias Name for Leads')
    generate_lead_from_alias = fields.Boolean('Manual Assignation of Emails', config_parameter='crm.generate_lead_from_alias')
    group_use_lead = fields.Boolean(string="Leads", implied_group='crm.group_use_lead')
    module_crm_phone_validation = fields.Boolean("Phone Validation")
    module_web_clearbit = fields.Boolean("Customer Autocomplete")

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

    @api.onchange('group_use_lead')
    def _onchange_group_use_lead(self):
        """ Reset alias / leads configuration if leads are not used """
        if not self.group_use_lead:
            self.generate_lead_from_alias = False

    @api.onchange('generate_lead_from_alias')
    def _onchange_generate_lead_from_alias(self):
        self.crm_alias_prefix = 'info' if self.generate_lead_from_alias else False

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        alias = self._find_default_lead_alias_id()
        res.update(
            crm_alias_prefix=alias.alias_name if alias else False,
        )
        return res

    @api.multi
    def set_values(self):
        super(ResConfigSettings, self).set_values()
        alias = self._find_default_lead_alias_id()
        if alias:
            alias.write({'alias_name': self.crm_alias_prefix})
        else:
            self.env['mail.alias'].with_context(
                alias_model_name='crm.lead',
                alias_parent_model_name='crm.team').create({'alias_name': self.crm_alias_prefix})
