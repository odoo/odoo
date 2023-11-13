# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_it_edi_register = fields.Boolean(
        compute='_compute_l10n_it_edi_register',
        inverse='_set_l10n_it_edi_register_mode')
    l10n_it_edi_mode = fields.Selection(
        [('demo', 'Demo'),
         ('test', 'Test (experimental)'),
         ('prod', 'Official')],
        compute='_compute_l10n_it_edi_mode',
        inverse='_set_l10n_it_edi_register_mode',
        readonly=False)

    @api.depends('company_id.l10n_it_edi_proxy_user_id')
    def _compute_l10n_it_edi_mode(self):
        for config in self:
            config.l10n_it_edi_mode = config.company_id.l10n_it_edi_proxy_user_id.edi_mode

    @api.depends('company_id.l10n_it_edi_proxy_user_id')
    def _compute_l10n_it_edi_register(self):
        """Needed because it expects a compute"""
        for config in self:
            config.l10n_it_edi_register = bool(config.company_id.l10n_it_edi_proxy_user_id)

    def button_create_proxy_user(self):
        self.env['account_edi_proxy_client.user']._register_proxy_user(self.company_id, 'l10n_it_edi', self.l10n_it_edi_mode)

    def _set_l10n_it_edi_register_mode(self):
        for config in self.filtered(lambda x: x.l10n_it_edi_register):

            # Disable all users
            ProxyUser = config.env['account_edi_proxy_client.user']
            proxy_users = ProxyUser.sudo().with_context(active_test=False).search([
                ('company_id', '=', config.company_id.id),
                ('proxy_type', '=', 'l10n_it_edi')])
            proxy_users.active = False

            # Create or enable selected user
            new_edi_mode = config.l10n_it_edi_mode
            if selected_proxy_user := proxy_users.filtered(lambda x: x.edi_mode == new_edi_mode):
                selected_proxy_user.active = True
            else:
                config.env['account_edi_proxy_client.user']._register_proxy_user(config.company_id, 'l10n_it_edi', new_edi_mode)
