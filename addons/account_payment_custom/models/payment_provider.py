# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    # === CRUD METHODS === #

    @api.model_create_multi
    def create(self, vals_list):
        """Enable the cron to confirm wire transfers if provider Wire Transfer is enabled."""
        providers = super().create(vals_list)
        if any(
            p.code == "custom"
            and p.custom_mode == "wire_transfer"
            and p.state in ("enabled", "test")
            for p in providers
        ):
            self._toggle_confirm_wire_transfer_transactions_cron()
        return providers

    def write(self, vals):
        """Enable the cron to confirm wire transfers if provider Wire Transfer is enabled."""
        res = super().write(vals)
        if "state" in vals and any(
            p.code == "custom" and p.custom_mode == "wire_transfer" for p in self
        ):
            self._toggle_confirm_wire_transfer_transactions_cron()
        return res

    @api.model
    def _toggle_confirm_wire_transfer_transactions_cron(self):
        """Enable the cron to confirm wire transfers if provider Wire Transfer is enabled.

        This allows for saving resources on the cron's wake-up overhead when it has nothing to do.

        :return: None
        """
        wire_transfer_cron = self.env.ref(
            "account_payment_custom.cron_auto_confirm_paid_wire_transfer_txs", False
        )
        if wire_transfer_cron:
            any_active_wire_transfer_provider = bool(
                self.sudo().search_count(
                    [
                        ("code", "=", "custom"),
                        ("custom_mode", "=", "wire_transfer"),
                        ("state", "in", ("enabled", "test")),
                    ],
                    limit=1,
                )
            )
            wire_transfer_cron.active = any_active_wire_transfer_provider

    # === SETUP METHODS === #

    def _get_code(self):
        """Override of `payment` to consider the custom_mode as the code for 'wire_transfer'."""
        res = super()._get_code()
        if self.code == "custom" and self.custom_mode == "wire_transfer":
            return self.custom_mode
        return res
