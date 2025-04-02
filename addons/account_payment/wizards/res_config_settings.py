# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pay_invoices_online = fields.Boolean(config_parameter='account_payment.enable_portal_payment')

    providers_state = fields.Selection(
        selection=[
            ('none', 'None'),
            ('primary_provider', 'Primary Provider'),
            ('other', 'Other Provider')
        ],
        compute='_compute_providers_state',
    )
    primary_provider_label = fields.Char(compute='_compute_providers_state')
    onboarding_payment_method = fields.Selection(
        related='company_id.payment_onboarding_payment_method',
    )

    def _get_activated_providers(self):
        self.ensure_one()
        return self.env['payment.provider'].search([
            ('state', '!=', 'disabled'),
            ('code', 'not in', ['custom', 'demo']),
        ])

    def _compute_providers_state(self):
        for config in self:
            providers = config._get_activated_providers()
            primary_provider = next(
                (p for p in providers if p and p.code == config.onboarding_payment_method),
                None
            )

            config.providers_state = (
                'primary_provider' if primary_provider else 'other' if providers else 'none'
            )
            config.primary_provider_label = (
                self.env._('Configure %s', primary_provider.name) if primary_provider else ''
            )

    def _activate_payment_provider(self, menu_id):
        self.ensure_one()
        if not self.onboarding_payment_method:
            return False

        return self.env.company._run_payment_onboarding_step(menu_id=menu_id)

    def action_configure_first_provider(self):
        self.ensure_one()
        provider = self.env['payment.provider'].search([
            *self.env['payment.provider']._check_company_domain(self.env.company),
            ('code', '=', self.onboarding_payment_method)
        ], limit=1)
        providers = self._get_activated_providers()
        return {
            'name': self.primary_provider_label,
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'payment.provider',
            'views': [[False, 'form']],
            'res_id': provider.id if provider in providers else False,
        }
