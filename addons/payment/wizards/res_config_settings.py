# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.fields import Domain


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    installed_provider_id = fields.Many2one(
        string="Installed Provider",
        comodel_name="payment.provider",
        compute="_compute_installed_provider_id",
    )
    onboarding_payment_module = fields.Selection(related="company_id.onboarding_payment_module")

    # === COMPUTE METHODS === #

    @api.depends("company_id")
    def _compute_installed_provider_id(self):
        for config in self:
            installed_providers_domain = config._get_installed_providers_domain()
            if installed_providers := self.env["payment.provider"].search(
                installed_providers_domain, limit=1
            ):
                config.installed_provider_id = installed_providers[0]
            else:
                config.installed_provider_id = None

    def _get_installed_providers_domain(self):
        """Return the domain to search for installed providers.

        :return: The installed providers domain.
        :rtype: Domain
        """
        return Domain.AND([
            [("module_state", "=", "installed")],
            self.env["payment.provider"]._check_company_domain(self.company_id),
        ])

    # === ACTION METHODS === #

    def action_view_installed_provider(self):
        provider = self.installed_provider_id.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "payment.provider",
            "views": [[False, "form"]],
            "res_id": provider.id,
        }
