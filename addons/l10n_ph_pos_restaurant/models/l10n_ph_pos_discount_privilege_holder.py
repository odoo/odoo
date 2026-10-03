# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class L10nPhPosDiscountPrivilegeHolder(models.Model):
    _name = "l10n_ph.pos.discount.privilege.holder"
    _inherit = ["pos.load.mixin"]
    _description = "Philippines POS SC/PWD Discount Privilege ID Holder"
    _check_company_auto = True

    order_id = fields.Many2one(
        "pos.order",
        string="Order",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(
        "res.company",
        related="order_id.company_id",
        store=True,
        index=True,
    )
    privilege_id = fields.Many2one(
        "l10n_ph.discount.privilege",
        string="Discount Privilege",
        required=True,
        check_company=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Related Contact",
        help="Optional link to a registered contact whose stored ID information "
        "was used to prefill this ID holder.",
    )
    name = fields.Char(string="ID Holder Name", required=True)
    id_number = fields.Char(string="ID Number", required=True)
    is_present = fields.Boolean(
        string="Is ID Holder Present?",
        default=True,
        help="Unchecked when an authorized representative claims the discount "
        "on the ID holder's behalf (BIR RMC 71-2022).",
    )
    representative_name = fields.Char(string="Representative Name")
    representative_id = fields.Char(string="Representative ID")

    # --- pos.load.mixin ---
    # Never bulk-preloaded at session start (not part of
    # pos.session._load_pos_data_models): holders are only ever fetched
    # on-demand, as part of the l10n_ph_apply_discount_privileges response.

    @api.model
    def _load_pos_data_domain(self, data):
        return [("order_id", "in", data["pos.order"].ids)]

    @api.model
    def _load_pos_data_fields(self, config):
        return [
            "id", "order_id", "privilege_id", "partner_id", "name", "id_number",
            "is_present", "representative_name", "representative_id",
        ]
