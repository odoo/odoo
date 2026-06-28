# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    # === CRUD METHODS === #

    @api.model_create_multi
    def create(self, vals_list):
        """Enable the cron to confirm wire transfers if a Wire Transfer provider is created."""
        providers = super().create(vals_list)
        if any(p.custom_mode == "wire_transfer" for p in providers):
            self._toggle_confirm_wire_transfer_transactions_cron()
        return providers

    @api.model
    def _toggle_confirm_wire_transfer_transactions_cron(self):
        """Enable the cron to confirm wire transfers if a Wire Transfer provider exists.

        This allows for saving resources on the cron's wake-up overhead when it has nothing to do.

        :return: None
        """
        wire_transfer_cron = self.env.ref(
            "account_payment_custom.cron_auto_confirm_paid_wire_transfer_txs", False
        )
        if wire_transfer_cron:
            any_wire_transfer_provider = bool(
                self.sudo().search_count([("custom_mode", "=", "wire_transfer")], limit=1)
            )
            wire_transfer_cron.active = any_wire_transfer_provider

    # === SETUP METHODS === #

    @api.model
    def _setup_provider(self, *args, custom_mode=None, **kwargs):
        """Override of `payment` to enable the cron to confirm wire transfers."""
        super()._setup_provider(*args, custom_mode=custom_mode, **kwargs)
        if custom_mode == "wire_transfer":
            self._toggle_confirm_wire_transfer_transactions_cron()

    @api.model
    def _remove_provider(self, *args, custom_mode=None, **kwargs):
        """Override of `payment` to disable the cron to confirm wire transfers."""
        super()._remove_provider(*args, custom_mode=custom_mode, **kwargs)
        if custom_mode == "wire_transfer":
            self._toggle_confirm_wire_transfer_transactions_cron()

    def _get_code(self):
        """Override of `payment` to consider the custom_mode as the code for 'wire_transfer'."""
        res = super()._get_code()
        if self.code == "custom" and self.custom_mode == "wire_transfer":
            return self.custom_mode
        return res
