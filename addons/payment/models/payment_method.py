# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Domain

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.const import REPORT_REASONS_MAPPING


class PaymentMethod(models.Model):
    _name = "payment.method"
    _description = "Payment Method"
    _order = "active desc, sequence, name"

    name = fields.Char(string="Name", required=True, translate=True)
    code = fields.Char(
        string="Code", help="The technical code of this payment method.", required=True
    )
    sequence = fields.Integer(string="Sequence", default=1000)
    primary_payment_method_id = fields.Many2one(
        string="Primary Payment Method",
        help="The primary payment method of the current payment method, if the latter is a brand."
        '\nFor example, "Card" is the primary payment method of the card brand "VISA".',
        comodel_name="payment.method",
        index="btree_not_null",
    )
    brand_ids = fields.One2many(
        string="Brands",
        help="The brands of the payment methods that will be displayed on the payment form.",
        comodel_name="payment.method",
        inverse_name="primary_payment_method_id",
        context={"active_test": False},
    )
    is_primary = fields.Boolean(
        string="Is Primary Payment Method",
        compute="_compute_is_primary",
        search="_search_is_primary",
    )
    provider_id = fields.Many2one(
        string="Provider",
        help="The provider supporting this payment method.",
        comodel_name="payment.provider",
        ondelete="cascade",
        required=True,
        index=True,
    )
    active = fields.Boolean(string="Active")
    image = fields.Image(
        string="Image",
        help="The base image used for this payment method; in a 64x64 px format.",
        max_width=64,
        max_height=64,
        required=True,
    )
    image_payment_form = fields.Image(
        string="The resized image displayed on the payment form.",
        related="image",
        max_width=45,
        max_height=30,
        store=True,
    )

    # Feature support fields.
    support_tokenization = fields.Boolean(
        string="Tokenization",
        help="Tokenization is the process of saving the payment details as a token that can later"
        " be reused without having to enter the payment details again.",
    )
    support_express_checkout = fields.Boolean(
        string="Express Checkout",
        help="Express checkout allows customers to pay faster by using a payment method that"
        " provides all required billing and shipping information, thus allowing to skip the"
        " checkout process.",
    )
    support_manual_capture = fields.Selection(
        string="Manual Capture",
        help="The payment is authorized and captured in two steps instead of one.",
        selection=[
            ("none", "Unsupported"),
            ("full_only", "Full Only"),
            ("partial", "Full & Partial"),
        ],
        default="none",
        required=True,
    )
    support_refund = fields.Selection(
        string="Refund",
        help="Refund is a feature allowing to refund customers directly from the payment in Odoo.",
        selection=[
            ("none", "Unsupported"),
            ("full_only", "Full Only"),
            ("partial", "Full & Partial"),
        ],
        default="none",
        required=True,
    )
    supported_country_ids = fields.Many2many(
        string="Countries",
        help="The list of countries in which this payment method can be used (if the provider"
        " allows it). In other countries, this payment method is not available to customers.",
        comodel_name="res.country",
    )
    supported_currency_ids = fields.Many2many(
        string="Currencies",
        help="The list of currencies for that are supported by this payment method (if the provider"
        " allows it). When paying with another currency, this payment method is not available to"
        " customers.",
        comodel_name="res.currency",
        context={"active_test": False},
    )

    # === SQL CONSTRAINTS === #

    _provider_id_code_uniq = models.Constraint(
        "UNIQUE(provider_id, code)", "The provider already has a payment method with this code."
    )

    # === COMPUTE METHODS === #

    def _compute_is_primary(self):
        for payment_method in self:
            payment_method.is_primary = not payment_method.primary_payment_method_id

    def _search_is_primary(self, operator, value):  # noqa: ARG002
        if operator not in ("in", "not in"):
            return NotImplemented
        return [("primary_payment_method_id", operator, [False])]

    # === ONCHANGE METHODS === #

    @api.onchange("active", "support_tokenization")
    def _onchange_warn_before_disabling_tokens(self):
        """Warn the user that tokens linked to the payment method get archived when its archived or
        when support for tokenization is removed.

        :return: A client action with the warning message, if any.
        :rtype: dict
        """
        if not self.active or not self.support_tokenization:
            related_tokens = (
                self
                .env["payment.token"]
                .with_context(active_test=True)  # Fix the context forwarded by the view.
                .search(Domain("payment_method_id", "in", (self + self.brand_ids).ids))
            )
            if related_tokens:
                return {
                    "warning": {
                        "title": self.env._("Warning"),
                        "message": self.env._(
                            "This action will also archive %s tokens that are registered with this"
                            " payment method.",
                            len(related_tokens),
                        ),
                    }
                }

    # === CONSTRAINT METHODS === #

    @api.constrains("active", "support_manual_capture")
    def _check_manual_capture_supported_by_provider(self):
        incompatible_pms = self.filtered(
            lambda pm: (
                pm.active
                and (pm.primary_payment_method_id or pm).support_manual_capture == "none"
                and pm.provider_id.capture_manually
            )
        )
        if incompatible_pms:
            raise ValidationError(
                self.env._(
                    "The following payment methods cannot be enabled because their payment provider"
                    " has manual capture activated: %s",
                    ", ".join(incompatible_pms.mapped("name")),
                )
            )

    # === CRUD METHODS === #

    def write(self, vals):
        # Match the "active" status of brands when the payment method is activated/deactivated
        if "active" in vals:
            self.brand_ids.active = vals["active"]

        # Archive tokens when the payment method is archived or tokenization support is removed
        if vals.get("active") is False or vals.get("support_tokenization") is False:
            linked_tokens = (
                self
                .env["payment.token"]
                .with_context(active_test=True)  # Fix the context forwarded by the view
                .search(Domain("payment_method_id", "in", (self + self.brand_ids).ids))
            )
            linked_tokens.active = False

        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_if_not_default_payment_method(self):
        if any(pm.code == "unknown" for pm in self):
            raise UserError(self.env._("You cannot delete the default payment method."))

    # === BUSINESS METHODS === #

    def _deduplicate_by_code(self, report=None):
        """Sort and deduplicate payment methods by code, keeping the best-ranked match.

        The payment methods are first sorted by display order (see `_sort_by_display_order`), then
        all but the first occurrence of each code are dropped.

        :param dict report: The report into which availability statuses are to be logged
        :return: The deduplicated payment methods
        :rtype: payment.method
        """
        # Sort payment methods by their display order
        sorted_payment_methods = self._sort_by_display_order()

        # Deduplicate payment methods by code
        deduplicated_payment_methods = self.env["payment.method"].concat(
            payment_method_group[:1]
            for payment_method_group in sorted_payment_methods.grouped("code").values()
        )

        # Log availability statuses in the report
        payment_utils.add_to_report(
            report,
            self - deduplicated_payment_methods,
            available=False,
            reason=REPORT_REASONS_MAPPING["duplicate_code"],
        )

        # Sort the whole report, including already logged PM availability statues
        if report and "payment_methods" in report:
            sorted_logged_pms = (
                self
                .env["payment.method"]
                .concat(report["payment_methods"])
                ._sort_by_display_order()
            )
            report["payment_methods"] = {
                pm: report["payment_methods"][pm] for pm in sorted_logged_pms
            }

        return deduplicated_payment_methods

    def _sort_by_display_order(self):
        """Sort payment methods by their display order.

        The display order is: provider sequence > provider name > PM sequence > PM name.

        :return: The sorted payment methods
        :rtype: payment.method
        """
        return self.sorted(
            key=lambda pm: (pm.provider_id.sequence, pm.provider_id.name, pm.sequence, pm.name)
        )

    def _is_postpaid(self):
        """Return whether the payment method is postpaid.

        :return: Whether the payment method is postpaid
        :rtype: bool
        """
        return False
