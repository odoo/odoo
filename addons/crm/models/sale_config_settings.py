# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class CRMSettings(models.TransientModel):
    _inherit = 'sale.config.settings'

    alias_prefix = fields.Char('Default Alias Name for Leads')
    alias_domain = fields.Char('Alias Domain', default=lambda self: self.env["ir.config_parameter"].sudo().get_param("mail.catchall.domain"))
    generate_lead_from_alias = fields.Boolean('Manual Assignation of Emails')
    group_use_lead = fields.Boolean(string="Leads", implied_group='crm.group_use_lead')
    module_crm_phone_validation = fields.Boolean("Phone Validation")
    module_crm_voip = fields.Boolean("Asterisk (VoIP)")

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
        self.alias_prefix = 'info' if self.generate_lead_from_alias else False

    @api.model
    def get_default_alias_prefix(self, fields):
        alias = self._find_default_lead_alias_id()
        return {'alias_prefix': alias.alias_name if alias else False}

    @api.multi
    def set_default_alias_prefix(self):
        for record in self:
            alias = self._find_default_lead_alias_id()
            if alias:
                alias.write({'alias_name': record.alias_prefix})
            else:
                self.env['mail.alias'].with_context(alias_model_name='crm.lead', alias_parent_model_name='crm.team').create({'alias_name': record.alias_prefix})

        return True

    @api.model
    def get_default_generate_lead_from_alias(self, fields):
        return {
            'generate_lead_from_alias': self.env['ir.config_parameter'].sudo().get_param('crm.generate_lead_from_alias')
        }

    @api.multi
    def set_generate_lead_from_alias(self):
        self.env['ir.config_parameter'].sudo().set_param('crm.generate_lead_from_alias', self.generate_lead_from_alias)
