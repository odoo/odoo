# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _
from odoo.exceptions import UserError

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    is_edi_proxy_active = fields.Boolean(compute='_compute_is_edi_proxy_active')
    l10n_it_edi_proxy_current_state = fields.Char(compute='_compute_l10n_it_edi_proxy_current_state')
    l10n_it_edi_register = fields.Boolean(compute='_compute_l10n_it_edi_register', inverse='_set_l10n_it_edi_register_demo_mode')
    l10n_it_edi_demo_mode = fields.Selection(
        [('demo', 'Demo'),
         ('test', 'Test (experimental)'),
         ('prod', 'Official')],
        compute='_compute_l10n_it_edi_demo_mode',
        inverse='_set_l10n_it_edi_register_demo_mode',
        readonly=False)

    def _create_proxy_user(self, company_id, edi_mode):
        self.env['account_edi_proxy_client.user']._register_proxy_user(company_id, 'l10n_it_edi', edi_mode)

    def button_create_proxy_user(self):
        self._create_proxy_user(self.company_id, self.l10n_it_edi_demo_mode)

    @api.depends('company_id.account_edi_proxy_client_ids', 'company_id.account_edi_proxy_client_ids.active')
    def _compute_l10n_it_edi_demo_mode(self):
        for config in self:
            edi_user = self.env['account_edi_proxy_client.user'].search([
                ('company_id', '=', config.company_id.id),
                ('proxy_type', '=', 'l10n_it_edi'),
            ], limit=1)
            config.l10n_it_edi_demo_mode = edi_user.edi_mode or 'demo'

    @api.depends('company_id.account_edi_proxy_client_ids', 'company_id.account_edi_proxy_client_ids.active')
    def _compute_is_edi_proxy_active(self):
        for config in self:
            config.is_edi_proxy_active = config.company_id.account_edi_proxy_client_ids

    @api.depends('company_id.account_edi_proxy_client_ids', 'company_id.account_edi_proxy_client_ids.active')
    def _compute_l10n_it_edi_proxy_current_state(self):
        for config in self:
            proxy_user = config.company_id.account_edi_proxy_client_ids.search([
                ('company_id', '=', config.company_id.id),
                ('proxy_type', '=', 'l10n_it_edi'),
            ], limit=1)

            config.l10n_it_edi_proxy_current_state = 'inactive' if not proxy_user else 'demo' if proxy_user.id_client[:4] == 'demo' else 'active'

    @api.depends('company_id')
    def _compute_l10n_it_edi_register(self):
        """Needed because it expects a compute"""
        self.l10n_it_edi_register = False

    def _set_l10n_it_edi_register_demo_mode(self):
        for config in self:

            proxy_user = self.env['account_edi_proxy_client.user'].search([
                ('company_id', '=', config.company_id.id),
                ('proxy_type', '=', 'l10n_it_edi'),
            ], limit=1)

            real_proxy_users = self.env['account_edi_proxy_client.user'].sudo().search([
                ('company_id', '=', config.company_id.id),
                ('proxy_type', '=', 'l10n_it_edi'),
                ('id_client', 'not like', 'demo'),
            ])

            # Update the config as per the selected radio button
            previous_demo_state = proxy_user.edi_mode
            edi_mode = config.l10n_it_edi_demo_mode

            # If the user is trying to change from a state in which they have a registered official or testing proxy client
            # to another state, we should stop them
            if real_proxy_users and previous_demo_state != edi_mode:
                raise UserError(_("The company has already registered with the service as 'Test' or 'Official', it cannot change."))

            if config.l10n_it_edi_register:
                # There should only be one user at a time, if there are no users, register one
                if not proxy_user:
                    self._create_proxy_user(config.company_id, edi_mode)
                    return

                # If there is a demo user, and we are transitioning from demo to test or production, we should
                # delete all demo users and then create the new user.
                elif proxy_user.id_client[:4] == 'demo' and edi_mode != 'demo':
                    self.env['account_edi_proxy_client.user'].search([
                        ('company_id', '=', config.company_id.id),
                        ('proxy_type', '=', 'l10n_it_edi'),
                        ('id_client', '=like', 'demo%'),
                    ]).sudo().unlink()
                    self._create_proxy_user(config.company_id, edi_mode)
