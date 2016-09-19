# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class BaseConfigSettings(models.TransientModel):

    _name = 'base.config.settings'
    _inherit = 'res.config.settings'

    group_multi_company = fields.Boolean(string='Manage multiple companies',
        help='Work in multi-company environments, with appropriate security access between companies.',
        implied_group='base.group_multi_company')
    company_id = fields.Many2one('res.company', string='Company', required=True,
        default=lambda self: self.env.user.company_id)
    module_share = fields.Boolean(string='Allow documents sharing',
        help="""Share or embed any screen of Odoo.""")
    module_portal = fields.Boolean(string='Activate the customer portal',
        help="""Give your customers access to their documents.""")
    module_auth_oauth = fields.Boolean(string='Use external authentication providers (OAuth)')
    module_base_import = fields.Boolean(string="Allow users to import data from CSV/XLS/XLSX/ODS files")
    module_google_drive = fields.Boolean(string='Attach Google documents to any record',
        help="""This installs the module google_docs.""")
    module_google_calendar = fields.Boolean(
        string='Allow the users to synchronize their calendar  with Google Calendar',
        help="""This installs the module google_calendar.""")
    module_inter_company_rules = fields.Boolean(string='Manage Inter Company',
        help="""This installs the module inter_company_rules.\n Configure company rules to automatically create SO/PO when one of your company sells/buys to another of your company.""")
    company_share_partner = fields.Boolean(string='Share partners to all companies',
        help="Share your partners to all companies defined in your instance.\n"
             " * Checked : Partners are visible for every companies, even if a company is defined on the partner.\n"
             " * Unchecked : Each company can see only its partner (partners where company is defined). Partners not related to a company are visible for all companies.")
    group_multi_currency = fields.Boolean(string='Allow multi currencies',
            implied_group='base.group_multi_currency',
            help="Allows to work in a multi currency environment")

    # Report config from base/res/res_company.py
    custom_footer = fields.Boolean(related="company_id.custom_footer", string="Custom footer *", help="Check this to define the report footer manually. Otherwise it will be filled in automatically.")
    rml_footer = fields.Text(related="company_id.rml_footer", string='Custom Report Footer *', help="Footer text displayed at the bottom of all reports.")
    rml_footer_readonly = fields.Text(related='rml_footer', string='Report Footer *', readonly=True)
    rml_paper_format = fields.Selection(related="company_id.rml_paper_format", string="Paper Format *", required=True)
    font = fields.Many2one(related='company_id.font', string="Font *", help="Set the font into the report header, it will be used as default font in the RML reports of the user company")
    rml_header = fields.Text(related="company_id.rml_header", string="RML Header *")
    rml_header2 = fields.Text(related="company_id.rml_header2", string='RML Internal Header *')
    rml_header3 = fields.Text(related="company_id.rml_header3", string='RML Internal Header for Landscape Reports *')


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
        action['context'] = self.env.context
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
