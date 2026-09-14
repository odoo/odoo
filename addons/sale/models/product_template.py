from collections import defaultdict

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.libs.debug_log import DebugLog
from odoo.tools.translate import _

_debug = DebugLog(__name__)


class ProductTemplate(models.Model):
    _inherit = "product.template"
    _check_company_auto = True

    service_type = fields.Selection(
        selection=[("manual", "Manually set quantities on order")],
        string="Track Service",
        compute="_compute_service_type",
        precompute=True,
        store=True,
        readonly=False,
        help="Manually set quantities on order: Invoice based on the manually entered quantity, without creating an analytic account.\n"
        "Timesheets on contract: Invoice based on the tracked hours on the related timesheet.\n"
        "Create a task and track hours: Create a task on the sales order validation and track the work hours.",
    )
    expense_policy = fields.Selection(
        selection=[
            ("no", "No"),
            ("cost", "At cost"),
            ("sales_price", "Sales price"),
        ],
        string="Re-Invoice Costs",
        compute="_compute_expense_policy",
        default="no",
        store=True,
        readonly=False,
        help="Validated expenses, vendor bills, or stock pickings (set up to track costs) can be invoiced to the customer at either cost or sales price.",
    )
    invoice_policy = fields.Selection(
        selection=[
            ("ordered", "Ordered quantities"),
            ("transferred", "Delivered quantities"),
        ],
        string="Invoicing Policy",
        compute="_compute_invoice_policy",
        precompute=True,
        store=True,
        readonly=False,
        tracking=True,
        help="Ordered Quantity: Invoice quantities ordered by the customer.\n"
        "Delivered Quantity: Invoice quantities delivered to the customer.",
    )
    sale_line_warn_msg = fields.Text(string="Sales Order Line Warning")
    visible_expense_policy = fields.Boolean(
        string="Re-Invoice Policy visible",
        compute="_compute_visible_expense_policy",
        depends_context=("uid",),
    )
    optional_product_ids = fields.Many2many(
        comodel_name="product.template",
        relation="product_optional_rel",
        column1="src_id",
        column2="dest_id",
        string="Optional Products",
        check_company=True,
        help="Optional Products are suggested "
        "whenever the customer hits *Add to Cart* (cross-sell strategy, "
        "e.g. for computers: warranty, software, etc.).",
    )
    sales_count = fields.Float(
        string="Sold",
        digits="Product Unit",
        compute="_compute_sales_count",
    )

    @api.constrains("company_id")
    def _check_sale_product_company(self):
        products_by_company = defaultdict(lambda: self.env["product.template"])
        for product in self:
            if not product.product_variant_ids or not product.company_id:
                continue
            products_by_company[product.company_id] |= product

        for target_company, products in products_by_company.items():
            subquery_products = (
                self.env["product.product"]
                .sudo()
                .with_context(active_test=False)
                ._search([("product_tmpl_id", "in", products.ids)])
            )
            so_lines = (
                self.env["sale.order.line"]  # noqa: E8507 - one query per company; templates sharing one were merged above
                .sudo()
                .search_read(
                    [
                        ("product_id", "in", subquery_products),
                        "!",
                        ("company_id", "child_of", target_company.id),
                    ],
                    fields=["id", "product_id"],
                )
            )
            _debug.perf.count(
                "product_company_probe",
                company=target_company,
                products=products,
                offending_lines=len(so_lines),
            )
            if so_lines:
                used_products = [sol["product_id"][1] for sol in so_lines]
                raise ValidationError(
                    _(
                        "The following products cannot be restricted to the company"
                        " %(company)s because they have already been used in quotations or "
                        "sales orders in another company:\n%(used_products)s\n"
                        "You can archive these products and recreate them "
                        "with your company restriction instead, or leave them as "
                        "shared product.",
                        company=target_company.name,
                        used_products=", ".join(used_products),
                    ),
                )

    @api.constrains(lambda self: self._get_incompatible_types())
    def _check_incompatible_types(self):
        incompatible_types = self._get_incompatible_types()
        if len(incompatible_types) < 2:
            _debug.logic("incompatible_types_skipped", declared=len(incompatible_types))
            return
        fields = (
            self.env["ir.model.fields"]
            .sudo()
            .search_read(
                [
                    ("model", "=", "product.template"),
                    ("name", "in", incompatible_types),
                ],
                ["name", "field_description"],
            )
        )
        field_descriptions = {v["name"]: v["field_description"] for v in fields}
        field_list = incompatible_types + ["name"]
        values = self.read(field_list)
        for val in values:
            incompatible_fields = [f for f in incompatible_types if val[f]]
            if len(incompatible_fields) > 1:
                _debug.logic(
                    "incompatible_types_rejected",
                    product=val["name"],
                    fields=",".join(incompatible_fields),
                )
                raise ValidationError(
                    _(
                        "The product (%(product)s) has incompatible values: %(value_list)s",
                        product=val["name"],
                        value_list=[field_descriptions[v] for v in incompatible_fields],
                    ),
                )

    @api.depends("purchase_ok")
    def _compute_visible_expense_policy(self):
        visibility = self.env.user.has_group("analytic.group_analytic_accounting")
        for template in self:
            template.visible_expense_policy = visibility and template.purchase_ok

    @api.depends("sale_ok")
    def _compute_service_tracking(self):
        super()._compute_service_tracking()
        self.filtered(lambda pt: not pt.sale_ok).service_tracking = "no"

    @api.depends("sale_ok")
    def _compute_expense_policy(self):
        self.filtered(lambda t: not t.sale_ok).expense_policy = "no"

    @api.depends("product_variant_ids.sales_count")
    def _compute_sales_count(self):
        variants = self.with_context(active_test=False).product_variant_ids
        count_by_variant = {variant.id: variant.sales_count for variant in variants}
        _debug.perf.count(
            "template_sales_count", templates=len(self), variants=len(variants)
        )
        for template in self:
            template.sales_count = template.uom_id.round(
                sum(
                    count_by_variant.get(variant.id, 0.0)
                    for variant in template.with_context(
                        active_test=False,
                    ).product_variant_ids
                ),
            )

    @api.depends("type")
    def _compute_service_type(self):
        self.filtered(
            lambda t: t.type == "consu" or not t.service_type
        ).service_type = "manual"

    @api.depends("type")
    def _compute_invoice_policy(self):
        self.filtered(
            lambda t: t.type == "consu" or not t.invoice_policy,
        ).invoice_policy = "ordered"

    @api.depends("invoice_policy", "sale_ok", "service_tracking")
    def _compute_product_tooltip(self):
        super()._compute_product_tooltip()

    @api.onchange("type")
    def _onchange_type(self):
        res = super()._onchange_type()
        if self._origin and self.sales_count > 0:
            _debug.logic(
                "template_type_change_warning",
                template=self._origin,
                sold=self.sales_count,
            )
            res["warning"] = {
                "title": _("Warning"),
                "message": _(
                    "You cannot change the product's type because it is already used in sales orders."
                ),
            }
        return res

    @api.readonly
    def action_view_sales(self):
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "sale.action_sale_history"
        )
        action["domain"] = [
            "&",
            ("state", "=", "done"),
            (
                "product_id",
                "in",
                self.with_context(active_test=False).product_variant_ids.ids,
            ),
        ]
        action["display_name"] = _("Sales History for %s", self.display_name)
        return action

    def _get_backend_root_menu_ids(self):
        return super()._get_backend_root_menu_ids() + [
            self.env.ref("sale.sale_menu_root").id
        ]

    @api.model
    def get_import_templates(self):
        res = super().get_import_templates()
        if self.env.context.get("sale_multi_pricelist_product_template"):
            if self.env.user.has_group("product.group_product_pricelist"):
                return [
                    {
                        "label": _("Import Template for Products"),
                        "template": "/product/static/xls/product_template.xls",
                    },
                ]
        return res

    @api.model
    def _get_incompatible_types(self):
        return []

    def get_single_product_variant(self):
        res = super().get_single_product_variant()
        if res.get("product_id", False):
            has_optional_products = False
            for optional_product in self.product_variant_id.optional_product_ids:
                if (
                    optional_product.has_dynamic_attributes()
                    or optional_product._get_possible_variants(
                        self.product_variant_id.product_template_attribute_value_ids
                    )
                ):
                    has_optional_products = True
                    _debug.logic(
                        "optional_products_found",
                        template=self,
                        optional=optional_product,
                    )
                    break
            res.update(
                {
                    "has_optional_products": has_optional_products,
                    "is_combo": self.type == "combo",
                },
            )
        return res

    @api.model
    def _get_saleable_tracking_types(self):
        return ["no"]

    @api.model
    def _get_configurator_display_price(
        self,
        product_or_template,
        quantity,
        date,
        currency,
        pricelist,
        **kwargs,
    ):
        return self._get_configurator_price(
            product_or_template,
            quantity,
            date,
            currency,
            pricelist,
            **kwargs,
        )

    @api.model
    def _get_configurator_price(
        self,
        product_or_template,
        quantity,
        date,
        currency,
        pricelist,
        **kwargs,
    ):
        _debug.perf.count(
            "configurator_price",
            product=product_or_template,
            pricelist=pricelist,
            quantity=quantity,
        )
        return pricelist._get_product_price_rule(
            product_or_template,
            quantity=quantity,
            currency=currency,
            date=date,
            **kwargs,
        )

    @api.model
    def _get_additional_configurator_data(
        self,
        product_or_template,
        date,
        currency,
        pricelist,
        *,
        uom=None,
        **kwargs,
    ):
        return {}

    def _prepare_tooltip(self):
        tooltip = super()._prepare_tooltip()
        if not self.sale_ok:
            return tooltip

        invoicing_tooltip = self._prepare_invoicing_tooltip()

        tooltip = f"{tooltip} {invoicing_tooltip}" if tooltip else invoicing_tooltip

        if self.type == "service":
            additional_tooltip = self._prepare_service_tracking_tooltip()
            tooltip = (
                f"{tooltip} {additional_tooltip}" if additional_tooltip else tooltip
            )

        return tooltip

    def _prepare_invoicing_tooltip(self):
        _debug.logic(
            "invoicing_tooltip",
            template=self,
            policy=self.invoice_policy,
            type=self.type,
        )
        if self.invoice_policy == "transferred" and self.type != "consu":
            return _(
                "Invoice after delivery, based on quantities delivered, not ordered."
            )
        elif self.invoice_policy == "ordered" and self.type == "service":
            return _("Invoice ordered quantities as soon as this service is sold.")
        return ""

    def _prepare_service_tracking_tooltip(self):
        return ""
