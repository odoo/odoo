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
    use_root_proxy_user = fields.Boolean(compute='_compute_use_root_proxy_user')

    def _create_proxy_user(self, company_id, edi_mode):
        return self.env['account_edi_proxy_client.user']._register_proxy_user(company_id, 'l10n_it_edi', edi_mode)

    @api.depends('company_id')
    def _compute_l10n_it_edi_show_purchase_journal_id(self):
        for config in self:
            # Only show the setting when there exists more than 1 purchase journal.
            purchase_journal_count = self.env['account.journal'].search_count([
                *self.env['account.journal']._check_company_domain(config.company_id._l10n_it_get_edi_company()),
                ('type', '=', 'purchase'),
            ])
            config.l10n_it_edi_show_purchase_journal_id = purchase_journal_count >= 2

    @api.depends('company_id')
    def _compute_l10n_it_edi_register(self):
        for config in self:
            config.l10n_it_edi_register = config.company_id._l10n_it_get_edi_company().l10n_it_edi_register

    def _set_l10n_it_edi_register(self):
        for config in self:
            company = config.company_id._l10n_it_get_edi_company()
            company.l10n_it_edi_register = config.l10n_it_edi_register
            proxy_user = self.env['account_edi_proxy_client.user'].search([
                ('company_id', '=', company.id),
                ('proxy_type', '=', 'l10n_it_edi'),
                ('edi_mode', '!=', 'demo'),  # make sure it's a "real" proxy_user (edi_mode is 'test' or 'prod')
            ], limit=1)

            if proxy_user and proxy_user.active != config.l10n_it_edi_register:
                # Deactivate / Reactive the current proxy user based on the config's l10n_it_edi_register value
                proxy_user._toggle_proxy_user_active()
            elif config.l10n_it_edi_register and not proxy_user:
                # Create a new proxy user
                edi_mode = self.env['ir.config_parameter'].sudo().get_param('l10n_it_edi.proxy_user_edi_mode') or 'prod'
                proxy_user = self._create_proxy_user(company, edi_mode)

            if proxy_user:
                # Delete any previously created demo proxy user
                self.env['account_edi_proxy_client.user'].search([
                    ('company_id', '=', company.id),
                    ('proxy_type', '=', 'l10n_it_edi'),
                    ('edi_mode', '=', 'demo'),
                    ('id', '!=', proxy_user.id),
                ]).sudo().unlink()

    @api.depends('company_id.account_edi_proxy_client_ids', 'company_id.account_edi_proxy_client_ids.active')
    def _compute_use_root_proxy_user(self):
        for record in self:
            main_company = self.company_id.root_id
            edi_company = self.company_id._l10n_it_get_edi_company()
            record.use_root_proxy_user = edi_company == main_company and self.company_id != main_company
