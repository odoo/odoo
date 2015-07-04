# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models

class CrmConfiguration(models.TransientModel):
    _name = 'sale.config.settings'
    _inherit = ['sale.config.settings', 'fetchmail.config.settings']

    group_fund_raising = fields.Boolean(string="Manage Fund Raising",
        implied_group='crm.group_fund_raising',
        help="""Allows you to trace and manage your activities for fund raising.""")
    module_crm_claim = fields.Boolean(string="Manage Customer Claims",
        help='Allows you to track your customers/suppliers claims and grievances.\n'
             '-This installs the module crm_claim.')
    module_crm_helpdesk = fields.Boolean(string="Manage Helpdesk and Support",
        help='Allows you to communicate with Customer, process Customer query, and provide better help and support.\n'
             '-This installs the module crm_helpdesk.')
    alias_prefix = fields.Char(string='Default Alias Name for Leads')
    alias_domain = fields.Char(string='Alias Domain', default=lambda self: self.env["ir.config_parameter"].get_param("mail.catchall.domain"))
    group_scheduled_calls = fields.Boolean(string="Schedule calls to manage call center",
        implied_group='crm.group_scheduled_calls',
        help="""This adds the menu 'Scheduled Calls' under 'Sales / Phone Calls'""")

    def _find_default_lead_alias_id(self):
        alias = self.env.ref('crm.mail_alias_lead_info')
        if not alias:
            alias = self.env['mail.alias'].search(
                [
                    ('alias_model_id.model', '=', 'crm.lead'),
                    ('alias_force_thread_id', '=', False),
                    ('alias_parent_model_id.model', '=', 'crm.team'),
                    ('alias_parent_thread_id', '=', False),
                    ('alias_defaults', '=', '{}')
                ], limit=1)
        return alias

    @api.multi
    def get_default_alias_prefix(self):
        alias = self._find_default_lead_alias_id()
        return {'alias_prefix': alias.alias_name}

    @api.multi
    def set_default_alias_prefix(self):
        for record in self:
            alias = record._find_default_lead_alias_id()
            if not alias:
                alias = self.env['mail.alias'].with_context(alias_model_name='crm.lead', alias_parent_model_name='crm.team').create(
                    {'alias_name': record.alias_prefix})
            else:
                alias.write({'alias_name': record.alias_prefix})
        return True
