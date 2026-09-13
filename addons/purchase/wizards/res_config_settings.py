from odoo import _, api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    lock_confirmed_po = fields.Boolean(
        string="Lock Confirmed Purchase Orders",
        default=lambda self: self.env.company.order_lock_po == "lock",
    )
    order_lock_po = fields.Selection(
        related="company_id.order_lock_po",
        string="Purchase Order Modification *",
        readonly=False,
    )

    po_quotation_validity_days = fields.Integer(
        related="company_id.po_quotation_validity_days",
        readonly=False,
    )

    group_auto_done_setting = fields.Boolean(
        string="Lock Confirmed Purchases",
        implied_group="purchase.group_auto_done_setting",
    )
    group_warning_purchase = fields.Boolean(
        string="Purchase Warnings",
        implied_group="purchase.group_warning_purchase",
    )
    group_send_reminder = fields.Boolean(
        string="Receipt Reminder",
        default=True,
        implied_group="purchase.group_send_reminder",
        help="Allow automatically send email to remind your vendor the receipt date",
    )

    module_account_3way_match = fields.Boolean(
        string="3-way matching: purchases, receptions and bills"
    )
    module_purchase_requisition = fields.Boolean(string="Purchase Agreements")
    module_purchase_product_matrix = fields.Boolean(string="Purchase Grid Entry")

    @api.onchange("group_product_variant")
    def _onchange_group_product_variant_purchase(self):
        if self.module_purchase_product_matrix and not self.group_product_variant:
            self.module_purchase_product_matrix = False

    @api.onchange("module_purchase_product_matrix")
    def _onchange_module_purchase_product_matrix(self):
        if self.module_purchase_product_matrix and not self.group_product_variant:
            self.group_product_variant = True

    @api.onchange("po_quotation_validity_days")
    def _onchange_po_quotation_validity_days(self):
        return self._clamp_validity_days(
            "po_quotation_validity_days",
            _("RFQ Validity"),
        )

    def set_values(self):
        super().set_values()
        self._sync_order_lock("lock_confirmed_po", "order_lock_po")
