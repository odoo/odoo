# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.fields import Domain


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    active_provider_id = fields.Many2one(
        string="Active Provider",
        comodel_name='payment.provider',
        compute='_compute_active_provider_id',
    )
    has_enabled_provider = fields.Boolean(
        string="Has Enabled Provider", compute='_compute_has_enabled_provider'
    )
    onboarding_payment_module = fields.Selection(related='company_id.onboarding_payment_module')

    # === COMPUTE METHODS === #

    @api.depends('company_id')
    def _compute_active_provider_id(self):
        for config in self:
            active_providers_domain = config._get_active_providers_domain()
            if active_providers := self.env['payment.provider'].search(
                active_providers_domain, limit=1
            ):
                config.active_provider_id = active_providers[0]
            else:
                config.active_provider_id = None

    @api.depends('company_id')
    def _compute_has_enabled_provider(self):
        for config in self:
            enabled_providers_domain = config._get_active_providers_domain(enabled_only=True)
            config.has_enabled_provider = bool(
                self.env['payment.provider'].search(enabled_providers_domain, limit=1)
            )

    def _get_active_providers_domain(self, enabled_only=False):
        """Return the domain to search for active providers.

        :param bool enabled_only: Whether only enabled providers should be considered active.
        :return: The active providers domain.
        :rtype: Domain
        """
        company_domain = self.env['payment.provider']._check_company_domain(self.company_id)
        if enabled_only:
            return company_domain & Domain('state', '=', 'enabled')
        else:
            return company_domain & Domain('state', '!=', 'disabled')

    # === ACTION METHODS === #

    def action_view_active_provider(self):
        provider = self.active_provider_id.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'payment.provider',
            'views': [[False, 'form']],
            'res_id': provider.id,
        }
