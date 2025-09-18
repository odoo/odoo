from odoo import _, api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # Lock functionality
    lock_confirmed_po = fields.Boolean(
        string="Lock Confirmed Purchase Orders",
        default=lambda self: self.env.company.order_lock_po == "lock",
    )
    order_lock_po = fields.Selection(
        related="company_id.order_lock_po",
        string="Purchase Order Modification *",
        readonly=False,
    )

    # Quotation settings
    po_quotation_validity_days = fields.Integer(
        related="company_id.po_quotation_validity_days",
        readonly=False,
    )

    # Groups
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

    # Modules
    module_account_3way_match = fields.Boolean(
        string="3-way matching: purchases, receptions and bills",
    )
    module_purchase_requisition = fields.Boolean(string="Purchase Agreements")
    module_purchase_product_matrix = fields.Boolean(string="Purchase Grid Entry")

    # === ONCHANGE METHODS ===#

    @api.onchange("group_product_variant")
    def _onchange_group_product_variant_purchase(self):
        """If the user disables the product variants -> disable the product configurator as well"""
        if self.module_purchase_product_matrix and not self.group_product_variant:
            self.module_purchase_product_matrix = False

    @api.onchange("module_purchase_product_matrix")
    def _onchange_module_purchase_product_matrix(self):
        """The product variant grid requires the product variants activated.
        If the user enables the product configurator -> enable the product variants as well.
        """
        if self.module_purchase_product_matrix and not self.group_product_variant:
            self.group_product_variant = True

    @api.onchange("po_quotation_validity_days")
    def _onchange_po_quotation_validity_days(self):
        if self.po_quotation_validity_days < 0:
            self.po_quotation_validity_days = self.env["res.company"].default_get(
                ["po_quotation_validity_days"]
            )["po_quotation_validity_days"]
            return {
                "warning": {
                    "title": _("Warning"),
                    "message": _(
                        "RFQ Validity is required and must be greater or equal to 0."
                    ),
                },
            }

    # === CRUD METHODS ===#

    def set_values(self):
        super().set_values()
        # Synchronize lock_confirmed_po with order_lock_po
        order_lock_po = "lock" if self.lock_confirmed_po else "edit"
        if self.order_lock_po != order_lock_po:
            self.order_lock_po = order_lock_po
