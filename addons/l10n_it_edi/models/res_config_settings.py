# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_it_edi_register = fields.Boolean(
        compute='_compute_l10n_it_edi_register',
        inverse='_set_l10n_it_edi_register',
        readonly=False,
    )
    l10n_it_edi_purchase_journal_id = fields.Many2one(
        related='company_id.l10n_it_edi_purchase_journal_id',
        readonly=False,
    )
    l10n_it_edi_show_purchase_journal_id = fields.Boolean(compute='_compute_l10n_it_edi_show_purchase_journal_id')

    def _create_proxy_user(self, company_id, edi_mode):
        return self.env['account_edi_proxy_client.user']._register_proxy_user(company_id, 'l10n_it_edi', edi_mode)

    @api.depends('company_id')
    def _compute_l10n_it_edi_show_purchase_journal_id(self):
        for config in self:
            # Only show the setting when there exists more than 1 purchase journal.
            purchase_journal_count = self.env['account.journal'].search_count([
                *self.env['account.journal']._check_company_domain(config.company_id),
                ('type', '=', 'purchase'),
            ])
            config.l10n_it_edi_show_purchase_journal_id = purchase_journal_count >= 2

    @api.depends('company_id')
    def _compute_l10n_it_edi_register(self):
        for config in self:
            config.l10n_it_edi_register = config.company_id.l10n_it_edi_register

    def _set_l10n_it_edi_register(self):
        for config in self:
            config.company_id.l10n_it_edi_register = config.l10n_it_edi_register
            proxy_user = self.env['account_edi_proxy_client.user'].search([
                ('company_id', '=', config.company_id.id),
                ('proxy_type', '=', 'l10n_it_edi'),
                ('edi_mode', '!=', 'demo'),  # make sure it's a "real" proxy_user (edi_mode is 'test' or 'prod')
            ], limit=1)

            if proxy_user and proxy_user.active != config.l10n_it_edi_register:
                # Deactivate / Reactive the current proxy user based on the config's l10n_it_edi_register value
                proxy_user._toggle_proxy_user_active()
            elif config.l10n_it_edi_register and not proxy_user:
                # Create a new proxy user
                edi_mode = self.env['ir.config_parameter'].sudo().get_param('l10n_it_edi.proxy_user_edi_mode') or 'prod'
                self._create_proxy_user(config.company_id, edi_mode)
