# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _
from odoo.exceptions import UserError

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    is_edi_proxy_active = fields.Boolean(compute='_compute_is_edi_proxy_active')
    l10n_it_edi_proxy_current_state = fields.Char(compute='_compute_l10n_it_edi_proxy_current_state')
    l10n_it_edi_sdicoop_register = fields.Boolean(compute='_compute_l10n_it_edi_sdicoop_register', inverse='_set_l10n_it_edi_sdicoop_register_demo_mode')
    l10n_it_edi_sdicoop_demo_mode = fields.Selection(
        [('demo', 'Demo'),
         ('test', 'Test (experimental)'),
         ('prod', 'Official')],
        compute='_compute_l10n_it_edi_sdicoop_demo_mode',
        inverse='_set_l10n_it_edi_sdicoop_register_demo_mode',
        readonly=False)

    def _create_proxy_user(self, company_id):
        fattura_pa = self.env.ref('l10n_it_edi.edi_fatturaPA')
        edi_identification = fattura_pa._get_proxy_identification(company_id)
        self.env['account_edi_proxy_client.user']._register_proxy_user(company_id, fattura_pa, edi_identification)

    @api.depends('company_id.account_edi_proxy_client_ids', 'company_id.account_edi_proxy_client_ids.active')
    def _compute_l10n_it_edi_sdicoop_demo_mode(self):
        for config in self:
            config.l10n_it_edi_sdicoop_demo_mode = self.env['account_edi_proxy_client.user']._get_demo_state()

    def _set_l10n_it_edi_sdicoop_demo_mode(self):
        for config in self:
            self.env['ir.config_parameter'].set_param('account_edi_proxy_client.demo', config.l10n_it_edi_sdicoop_demo_mode)

    @api.depends('company_id.account_edi_proxy_client_ids', 'company_id.account_edi_proxy_client_ids.active')
    def _compute_is_edi_proxy_active(self):
        for config in self:
            config.is_edi_proxy_active = config.company_id.account_edi_proxy_client_ids

    @api.depends('company_id.account_edi_proxy_client_ids', 'company_id.account_edi_proxy_client_ids.active')
    def _compute_l10n_it_edi_proxy_current_state(self):
        fattura_pa = self.env.ref('l10n_it_edi.edi_fatturaPA')
        for config in self:
            proxy_user = config.company_id.account_edi_proxy_client_ids.search([
                ('company_id', '=', config.company_id.id),
                ('edi_format_id', '=', fattura_pa.id),
            ], limit=1)

            config.l10n_it_edi_proxy_current_state = 'inactive' if not proxy_user else 'demo' if proxy_user.id_client[:4] == 'demo' else 'active'

    @api.depends('company_id')
    def _compute_l10n_it_edi_sdicoop_register(self):
        """Needed because it expects a compute"""
        self.l10n_it_edi_sdicoop_register = False

    def button_create_proxy_user(self):
        # For now, only fattura_pa uses the proxy.
        # To use it for more, we have to either make the activation of the proxy on a format basis
        # or create a user per format here (but also when installing new formats)
        fattura_pa = self.env.ref('l10n_it_edi.edi_fatturaPA')
        edi_identification = fattura_pa._get_proxy_identification(self.company_id)
        if not edi_identification:
            return

        self.env['account_edi_proxy_client.user']._register_proxy_user(self.company_id, fattura_pa, edi_identification)

    def _set_l10n_it_edi_sdicoop_register_demo_mode(self):

        fattura_pa = self.env.ref('l10n_it_edi.edi_fatturaPA')
        for config in self:

            proxy_user = self.env['account_edi_proxy_client.user'].search([
                ('company_id', '=', config.company_id.id),
                ('edi_format_id', '=', fattura_pa.id)
            ], limit=1)

            real_proxy_users = self.env['account_edi_proxy_client.user'].sudo().search([
                ('id_client', 'not like', 'demo'),
            ])

            # Update the config as per the selected radio button
            previous_demo_state = proxy_user._get_demo_state()
            self.env['ir.config_parameter'].set_param('account_edi_proxy_client.demo', config.l10n_it_edi_sdicoop_demo_mode)

            # If the user is trying to change from a state in which they have a registered official or testing proxy client
            # to another state, we should stop them
            if real_proxy_users and previous_demo_state != config.l10n_it_edi_sdicoop_demo_mode:
                raise UserError(_("The company has already registered with the service as 'Test' or 'Official', it cannot change."))

            if config.l10n_it_edi_sdicoop_register:
                # There should only be one user at a time, if there are no users, register one
                if not proxy_user:
                    self._create_proxy_user(config.company_id)
                    return

                # If there is a demo user, and we are transitioning from demo to test or production, we should
                # delete all demo users and then create the new user.
                elif proxy_user.id_client[:4] == 'demo' and config.l10n_it_edi_sdicoop_demo_mode != 'demo':
                    self.env['account_edi_proxy_client.user'].search([('id_client', '=like', 'demo%')]).sudo().unlink()
                    self._create_proxy_user(config.company_id)
