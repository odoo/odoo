# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):

    _inherit = 'res.config.settings'

    group_multi_company = fields.Boolean("Manage multiple companies", implied_group='base.group_multi_company')
    company_id = fields.Many2one('res.company', string='Company', required=True,
        default=lambda self: self.env.user.company_id)
    default_user_rights = fields.Boolean("Default Access Rights")
    default_external_email_server = fields.Boolean("External Email Servers")
    module_base_import = fields.Boolean("Allow users to import data from CSV/XLS/XLSX/ODS files")
    module_google_calendar = fields.Boolean(
        string='Allow the users to synchronize their calendar  with Google Calendar')
    module_google_drive = fields.Boolean("Attach Google documents to any record")
    module_google_spreadsheet = fields.Boolean("Google Spreadsheet")
    module_auth_oauth = fields.Boolean("Use external authentication providers (OAuth)")
    module_auth_ldap = fields.Boolean("LDAP Authentication")
    module_base_gengo = fields.Boolean("Translate Your Website with Gengo")
    module_inter_company_rules = fields.Boolean("Manage Inter Company")
    module_pad = fields.Boolean("Collaborative Pads")
    module_voip = fields.Boolean("Asterisk (VoIP)")
    company_share_partner = fields.Boolean(string='Share partners to all companies',
        help="Share your partners to all companies defined in your instance.\n"
             " * Checked : Partners are visible for every companies, even if a company is defined on the partner.\n"
             " * Unchecked : Each company can see only its partner (partners where company is defined). Partners not related to a company are visible for all companies.")
    default_custom_report_footer = fields.Boolean("Custom Report Footer")
    report_footer = fields.Text(related="company_id.report_footer", string='Custom Report Footer', help="Footer text displayed at the bottom of all reports.")
    group_multi_currency = fields.Boolean(string='Multi-Currencies',
            implied_group='base.group_multi_currency',
            help="Allows to work in a multi currency environment")
    paperformat_id = fields.Many2one(related="company_id.paperformat_id", string='Paper format')
    external_report_layout = fields.Selection(related="company_id.external_report_layout")

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        params = self.env['ir.config_parameter'].sudo()
        default_external_email_server = params.get_param('base_setup.default_external_email_server', default=False)
        default_user_rights = params.get_param('base_setup.default_user_rights', default=False)
        default_custom_report_footer = params.get_param('base_setup.default_custom_report_footer', default=False)
        res.update(
            default_external_email_server=default_external_email_server,
            default_user_rights=default_user_rights,
            default_custom_report_footer=default_custom_report_footer,
            company_share_partner=not self.env.ref('base.res_partner_rule').active,
        )
        return res

    @api.multi
    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param("base_setup.default_external_email_server", self.default_external_email_server)
        self.env['ir.config_parameter'].sudo().set_param("base_setup.default_user_rights", self.default_user_rights)
        self.env['ir.config_parameter'].sudo().set_param("base_setup.default_custom_report_footer", self.default_custom_report_footer)
        self.env.ref('base.res_partner_rule').write({'active': not self.company_share_partner})

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
    def _prepare_report_view_action(self, template):
        template_id = self.env.ref(template)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ir.ui.view',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': template_id.id,
        }

    @api.multi
    def edit_external_header(self):
        return self._prepare_report_view_action('web.external_layout_' + self.external_report_layout)

    @api.multi
    def change_report_template(self):
        self.ensure_one()
        template = self.env.ref('base.view_company_report_form')
        return {
            'name': _('Choose Your Document Layout'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': self.env.user.company_id.id,
            'res_model': 'res.company',
            'views': [(template.id, 'form')],
            'view_id': template.id,
            'target': 'new',
        }
