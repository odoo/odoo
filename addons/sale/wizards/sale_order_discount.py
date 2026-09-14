from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.fields import Command
from odoo.libs.debug_log import DebugLog
from odoo.tools import float_repr

_debug = DebugLog(__name__)


class SaleOrderDiscount(models.TransientModel):
    _name = "sale.order.discount"
    _description = "Discount Wizard"

    sale_order_id = fields.Many2one(
        comodel_name="sale.order",
        default=lambda self: self.env.context.get("active_id"),
        required=True,
    )
    company_id = fields.Many2one(related="sale_order_id.company_id")
    currency_id = fields.Many2one(related="sale_order_id.currency_id")
    discount_amount = fields.Monetary(string="Amount")
    discount_percentage = fields.Float(string="Percentage")
    discount_type = fields.Selection(
        selection=[
            ("sol_discount", "On All Order Lines"),
            ("so_discount", "Global Discount"),
            ("amount", "Fixed Amount"),
        ],
        default="sol_discount",
    )

    @api.constrains("discount_type", "discount_percentage", "discount_amount")
    def _check_discount_amount(self):
        for wizard in self:
            if wizard.discount_type in ("sol_discount", "so_discount"):
                if wizard.discount_percentage > 1.0:
                    _debug.logic(
                        "discount_rejected",
                        wizard=wizard,
                        reason="over_100_percent",
                        percentage=wizard.discount_percentage,
                    )
                    raise ValidationError(
                        _("Discount percentage must be at most 100%.")
                    )
                if wizard.discount_percentage < 0.0:
                    _debug.logic(
                        "discount_rejected", wizard=wizard, reason="negative_percentage"
                    )
                    raise ValidationError(_("Discount percentage cannot be negative."))
            if wizard.discount_type == "amount":
                currency = wizard.currency_id or wizard.sale_order_id.currency_id
                if wizard.discount_amount < 0.0:
                    _debug.logic(
                        "discount_rejected", wizard=wizard, reason="negative_amount"
                    )
                    raise ValidationError(
                        _("The discount amount cannot be negative."),
                    )
                if (
                    currency.compare_amounts(
                        wizard.discount_amount, wizard.sale_order_id.amount_total
                    )
                    > 0
                ):
                    _debug.logic(
                        "discount_rejected",
                        wizard=wizard,
                        reason="over_order_total",
                        amount=wizard.discount_amount,
                    )
                    raise ValidationError(
                        _("The discount amount cannot exceed the order total."),
                    )

    def _prepare_discount_product_values(self):
        self.check_singleton()
        values = {
            "name": _("Discount"),
            "type": "service",
            "invoice_policy": "ordered",
            "list_price": 0.0,
            "company_id": self.company_id.id,
            "taxes_id": None,
        }
        services_category = self.env.ref(
            "product.product_category_services", raise_if_not_found=False
        )
        if services_category:
            values["categ_id"] = services_category.id
        return values

    def _prepare_global_discount_so_lines(self, base_lines):
        self.check_singleton()
        AccountTax = self.env["account.tax"]
        discount_dp = self.env["decimal.precision"].get_precision("Discount")
        has_multiple_tax_combinations = (
            len(
                {
                    base_line["tax_ids"]
                    for base_line in base_lines
                    if base_line["tax_ids"]
                }
            )
            > 1
        )
        so_line_values_list = []
        _debug.pipeline(
            "global_discount_lines",
            wizard=self,
            base_lines=len(base_lines),
            multiple_tax_combinations=has_multiple_tax_combinations,
        )
        for base_line in base_lines:
            if has_multiple_tax_combinations:
                if self.discount_type == "so_discount":
                    so_line_description = self.env._(
                        "Discount %(percent)s%% - On products with the following"
                        " taxes %(taxes)s",
                        percent=float_repr(
                            self.discount_percentage * 100.0, discount_dp
                        ),
                        taxes=", ".join(base_line["tax_ids"].mapped("name")),
                    )
                else:
                    so_line_description = self.env._(
                        "Discount - On products with the following taxes %(taxes)s",
                        taxes=", ".join(base_line["tax_ids"].mapped("name")),
                    )
            elif self.discount_type == "so_discount":
                so_line_description = self.env._(
                    "Discount %(percent)s%%",
                    percent=float_repr(self.discount_percentage * 100.0, discount_dp),
                )
            else:
                so_line_description = self.env._("Discount")

            so_line_values_list.append(
                {
                    "name": so_line_description,
                    "product_id": base_line["product_id"].id,
                    "price_unit": base_line["price_unit"],
                    "price_unit_auto": 0,
                    "tax_ids": [Command.set(base_line["tax_ids"].ids)],
                    "extra_tax_data": AccountTax._export_base_line_extra_tax_data(
                        base_line
                    ),
                    "sequence": 999,
                },
            )

        return so_line_values_list

    def _get_or_create_discount_product(self):
        self.check_singleton()
        company = self.company_id
        discount_product = company.sale_discount_product_id
        if not discount_product:
            if (
                self.env["product.product"].has_access("create")
                and company.has_access("write")
                and company._has_field_access(
                    company._fields["sale_discount_product_id"], "write"
                )
            ):
                company.sale_discount_product_id = self.env["product.product"].create(
                    self._prepare_discount_product_values()
                )
                _debug.lifecycle(
                    "discount_product_created",
                    company=company,
                    product=company.sale_discount_product_id,
                )
            else:
                _debug.logic(
                    "discount_product_refused", company=company, reason="no_access"
                )
                raise AccessError(
                    _(
                        "There does not seem to be any discount product configured for this company yet."
                        " You can either use a per-line discount, or ask an administrator to grant the"
                        " discount the first time.",
                    ),
                )
            discount_product = company.sale_discount_product_id
        return discount_product

    def _create_discount_lines(self):
        self.check_singleton()
        self = self.with_context(lang=self.sale_order_id._get_lang())

        discount_product = self._get_or_create_discount_product()

        if self.discount_type == "so_discount":
            amount_type = "percent"
            amount = self.discount_percentage * 100.0
        else:
            amount_type = "fixed"
            amount = self.discount_amount

        order = self.sale_order_id
        AccountTax = self.env["account.tax"]
        order_lines = order.line_ids.filtered(lambda x: not x.display_type)
        base_lines = [
            line._prepare_base_line_for_taxes_computation() for line in order_lines
        ]
        AccountTax._add_tax_details_in_base_lines(base_lines, order.company_id)
        AccountTax._round_base_lines_tax_details(base_lines, order.company_id)

        def grouping_function(base_line):
            return {"product_id": discount_product}

        global_discount_base_lines = AccountTax._prepare_global_discount_lines(
            base_lines=base_lines,
            company=self.company_id,
            amount_type=amount_type,
            amount=amount,
            computation_key=f"global_discount,{self.id}",
            grouping_function=grouping_function,
        )
        _debug.pipeline(
            "discount_lines_created",
            order=order,
            amount_type=amount_type,
            amount=amount,
            discount_lines=len(global_discount_base_lines),
        )
        order.line_ids = [
            Command.create(values)
            for values in self._prepare_global_discount_so_lines(
                global_discount_base_lines
            )
        ]

    def action_apply_discount(self):
        self.check_singleton()
        self = self.with_company(self.company_id)
        _debug.lifecycle(
            "discount_applied",
            order=self.sale_order_id,
            kind=self.discount_type,
            percentage=self.discount_percentage,
            amount=self.discount_amount,
        )
        if self.discount_type == "sol_discount":
            self.sale_order_id.line_ids.filtered(
                lambda line: not line.display_type and not line.is_downpayment
            ).write({"discount": self.discount_percentage * 100})
        else:
            self._create_discount_lines()
