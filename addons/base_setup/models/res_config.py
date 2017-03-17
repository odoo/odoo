# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class BaseConfigSettings(models.TransientModel):

    _name = 'base.config.settings'
    _inherit = 'res.config.settings'

    group_multi_company = fields.Boolean("Manage multiple companies", implied_group='base.group_multi_company')
    company_id = fields.Many2one('res.company', string='Company', required=True,
        default=lambda self: self.env.user.company_id)
    default_user_rights = fields.Boolean("Default Access Rights")
    default_external_email_server = fields.Boolean("External Email Servers")
    module_base_import = fields.Boolean("Allow users to import data from CSV/XLS/XLSX/ODS files")
    module_pad = fields.Boolean("External Pads")
    module_google_calendar = fields.Boolean(
        string='Allow the users to synchronize their calendar  with Google Calendar')
    module_google_drive = fields.Boolean("Attach Google documents to any record")
    module_google_spreadsheet = fields.Boolean("Google Spreadsheet")
    module_auth_oauth = fields.Boolean("Use external authentication providers (OAuth)")
    module_auth_ldap = fields.Boolean("LDAP Authentification")
    module_base_gengo = fields.Boolean("Translate Your Website with Gengo")
    module_inter_company_rules = fields.Boolean("Manage Inter Company")
    company_share_partner = fields.Boolean(string='Share partners to all companies',
        help="Share your partners to all companies defined in your instance.\n"
             " * Checked : Partners are visible for every companies, even if a company is defined on the partner.\n"
             " * Unchecked : Each company can see only its partner (partners where company is defined). Partners not related to a company are visible for all companies.")
    default_custom_report_footer = fields.Boolean("Custom Report Footer")
    rml_footer = fields.Text(related="company_id.rml_footer", string='Custom Report Footer', help="Footer text displayed at the bottom of all reports.")
    group_multi_currency = fields.Boolean(string='Allow multi currencies',
            implied_group='base.group_multi_currency',
            help="Allows to work in a multi currency environment")

    @api.model
    def get_default_fields(self, fields):
        default_external_email_server = self.env['ir.config_parameter'].sudo().get_param('base_setup.default_external_email_server', default=False)
        default_user_rights = self.env['ir.config_parameter'].sudo().get_param('base_setup.default_user_rights', default=False)
        default_custom_report_footer = self.env['ir.config_parameter'].sudo().get_param('base_setup.default_custom_report_footer', default=False)
        return {
            'default_external_email_server': default_external_email_server,
            'default_user_rights': default_user_rights,
            'default_custom_report_footer': default_custom_report_footer,
        }

    @api.multi
    def set_default_fields(self):
        self.env['ir.config_parameter'].sudo().set_param("base_setup.default_external_email_server", self.default_external_email_server)
        self.env['ir.config_parameter'].sudo().set_param("base_setup.default_user_rights", self.default_user_rights)
        self.env['ir.config_parameter'].sudo().set_param("base_setup.default_custom_report_footer", self.default_custom_report_footer)

    @api.multi
    def open_company(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'My Company',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'res.company',
            'res_id': self.env.user.company_id.id,
            'target': 'current',
        }
    @api.multi
    def open_default_user(self):
        action = self.env.ref('base.action_res_users').read()[0]
        action['res_id'] = self.env.ref('base.default_user').id
        action['views'] = [[self.env.ref('base.view_users_form').id, 'form']]
        return action

    @api.model
    def get_default_company_share_partner(self, fields):
        return {
            'company_share_partner': not self.env.ref('base.res_partner_rule').active
        }

    @api.multi
    def set_default_company_share_partner(self):
        partner_rule = self.env.ref('base.res_partner_rule')
        for config in self:
            partner_rule.write({'active': not config.company_share_partner})

    def act_discover_fonts(self):
        self.company_id.act_discover_fonts()
