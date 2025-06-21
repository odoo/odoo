# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _
from odoo.exceptions import UserError

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    is_edi_proxy_active = fields.Boolean(compute='_compute_is_edi_proxy_active')
    company_parent_id = fields.Many2one(related='company_id.parent_id', readonly=True)
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
            edi_user = config.company_id.l10n_it_edi_proxy_user_id
            config.l10n_it_edi_demo_mode = edi_user.edi_mode or 'demo'

    @api.depends('company_id.account_edi_proxy_client_ids', 'company_id.account_edi_proxy_client_ids.active')
    def _compute_is_edi_proxy_active(self):
        for config in self:
            config.is_edi_proxy_active = config.company_id.account_edi_proxy_client_ids

    @api.depends('company_id.account_edi_proxy_client_ids', 'company_id.account_edi_proxy_client_ids.active')
    def _compute_l10n_it_edi_proxy_current_state(self):
        for config in self:
            proxy_user = config.company_id.l10n_it_edi_proxy_user_id
            config.l10n_it_edi_proxy_current_state = 'inactive' if not proxy_user else 'demo' if proxy_user.id_client[:4] == 'demo' else 'active'

    @api.depends('company_id')
    def _compute_l10n_it_edi_register(self):
        """Needed because it expects a compute"""
        self.l10n_it_edi_register = False

    def _set_l10n_it_edi_register_demo_mode(self):
        for config in self:
            proxy_user = config.company_id.l10n_it_edi_proxy_user_id

            old_edi_mode = config.company_id.l10n_it_edi_proxy_user_id.edi_mode
            edi_mode = config.l10n_it_edi_demo_mode
            # If the user is trying to change from a state in which they have a registered official or testing proxy client
            # to another state, we should stop them
            if old_edi_mode not in ('demo', False, edi_mode):
                raise UserError(_("The company has already registered with the service as 'Test' or 'Official', it cannot change."))

            if config.l10n_it_edi_register:
                # If we are transitioning from a demo user
                # to test or production one, then we should
                # delete the old one before creating the new one.
                if old_edi_mode == 'demo' and edi_mode != 'demo':
                    proxy_user.sudo().unlink()
                self._create_proxy_user(config.company_id, edi_mode)
