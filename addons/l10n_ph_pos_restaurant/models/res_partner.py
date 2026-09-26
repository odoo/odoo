# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    l10n_ph_discount_privilege_id = fields.Many2one(
        "l10n_ph.discount.privilege",
        string="Discount Type",
        help="SC/PWD discount privilege this contact is registered under. "
        "Lets a frequent/regular diner's ID information prefill the POS "
        "Discount Privileges flow instead of being retyped every visit.",
    )
    l10n_ph_discount_privilege_id_number = fields.Char(string="Discount Privilege ID #")

    @api.model
    def _load_pos_data_fields(self, config):
        return [
            *super()._load_pos_data_fields(config),
            "l10n_ph_discount_privilege_id",
            "l10n_ph_discount_privilege_id_number",
        ]
