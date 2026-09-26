# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class PosSession(models.Model):
    _inherit = "pos.session"

    @api.model
    def _load_pos_data_models(self, config):
        return [
            *super()._load_pos_data_models(config),
            "l10n_ph.discount.privilege",
            # Registered (schema only — its domain yields no rows before any
            # order has holders) so the frontend's related_models registry
            # knows this model before l10n_ph_apply_discount_privileges hands
            # it fresh holder records to merge in.
            "l10n_ph.pos.discount.privilege.holder",
        ]
