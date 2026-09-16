import copy
import math
import re
from collections import defaultdict, deque
from itertools import batched

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Command, Domain
from odoo.libs.numbers import (
    float_compare,
    float_is_zero,
    float_repr,
    float_round,
)
from odoo.tools import frozendict, html2plaintext, is_html_empty
from odoo.tools.misc import clean_context
from odoo.tools.translate import html_translate

TYPE_TAX_USE = [
    ("sale", "Sales"),
    ("purchase", "Purchases"),
    ("none", "None"),
]


def _group_everything_together(base_line, tax_data):
    return True


def _group_by_tax(base_line, tax_data):
    return str(tax_data["tax"].id) if tax_data else None


class AccountTaxGroup(models.Model):
    _name = "account.tax.group"
    _description = "Tax Group"
    _order = "sequence asc, id"
    _check_company_auto = True
    _check_company_domain = models.check_companies_domain_parent_of

    name = fields.Char(
        translate=True,
        required=True,
    )
    sequence = fields.Integer(default=10)
    company_ids = fields.Many2many(
        comodel_name="res.company",
        string="Companies",
        depends_context=("uid",),
        default=lambda self: self.env.company,
        required=True,
    )
    country_id = fields.Many2one(
        comodel_name="res.country",
        compute="_compute_country_id",
        precompute=True,
        store=True,
        readonly=False,
        help="The country for which this tax group is applicable.",
    )
    country_code = fields.Char(related="country_id.code")
    preceding_subtotal = fields.Char(
        translate=True,
        help="If set, this value will be used on documents as the label of a "
        "subtotal excluding this tax group before displaying it. "
        "If not set, the tax group will be displayed after the "
        "'Untaxed amount' subtotal.",
    )
    pos_receipt_label = fields.Char(string="PoS receipt label")

    def _get_settings_company(self):
        return self.env.company

    @api.constrains("company_ids")
    def _check_company_ids_not_empty(self):
        self.invalidate_recordset(fnames=["company_ids"])
        if groups := self.filtered(lambda g: not g.sudo().company_ids):
            raise ValidationError(
                self.env._(
                    "The following tax groups must be assigned to at least "
                    "one company:\n%(groups)s",
                    groups="\n".join(f"- {group.display_name}" for group in groups),
                ),
            )

    @api.depends_context("company")
    def _compute_country_id(self):
        for group in self:
            company = group._get_settings_company()
            if "account_fiscal_country_id" in company._fields:
                group.country_id = (
                    company.account_fiscal_country_id or company.country_id
                )
            else:
                group.country_id = company.country_id


class AccountTax(models.Model):
    _name = "account.tax"
    _inherit = ["mixin.mail.thread"]
    _description = "Tax"
    _order = "sequence,id"
    _check_company_auto = True
    _rec_names_search = ["name", "description", "invoice_label"]
    _check_company_domain = models.check_companies_domain_parent_of
    _search_visibility_fields = ()

    name = fields.Char(
        string="Tax Name",
        translate=True,
        required=True,
        tracking=True,
    )
    type_tax_use = fields.Selection(
        selection=TYPE_TAX_USE,
        string="Tax Type",
        default="sale",
        required=True,
        tracking=True,
        help="Determines where the tax is selectable. Note: 'None' means a tax "
        "can't be used by itself, however it can still be used in a group.",
    )
    tax_scope = fields.Selection(
        selection=[("service", "Services"), ("consu", "Goods")]
    )
    amount_type = fields.Selection(
        selection=[
            ("group", "Group of Taxes"),
            ("fixed", "Fixed"),
            ("percent", "Percentage"),
            ("division", "Percentage Tax Included"),
        ],
        string="Tax Computation",
        default="percent",
        required=True,
        tracking=True,
        help="""
    - Group of Taxes: The tax is a set of sub taxes.
    - Fixed: The tax amount stays the same whatever the price.
    - Percentage: The tax amount is a % of the price:
        e.g 100 * (1 + 10%) = 110 (not price included)
        e.g 110 / (1 + 10%) = 100 (price included)
    - Percentage Tax Included: The tax amount is a division of the price:
        e.g 180 / (1 - 10%) = 200 (not price included)
        e.g 200 * (1 - 10%) = 180 (price included)
        """,
    )
    active = fields.Boolean(
        default=True,
        help="Set active to false to hide the tax without removing it.",
    )
    company_ids = fields.Many2many(
        comodel_name="res.company",
        string="Companies",
        depends_context=("uid",),
        default=lambda self: self.env.company,
        required=True,
    )
    children_tax_ids = fields.Many2many(
        comodel_name="account.tax",
        relation="account_tax_filiation_rel",
        column1="parent_tax",
        column2="child_tax",
        string="Children Taxes",
        check_company=True,
    )
    sequence = fields.Integer(
        default=1,
        required=True,
        help="The sequence field is used to define order in which the tax lines are applied.",
    )
    amount = fields.Float(
        digits=(16, 4),
        default=0.0,
        required=True,
        tracking=True,
    )
    description = fields.Html(translate=html_translate)
    invoice_label = fields.Char(
        string="Label on Invoices",
        translate=True,
    )
    tax_label = fields.Char(compute="_compute_tax_label")

    price_include = fields.Boolean(
        compute="_compute_price_include",
        search="_search_price_include",
        help="Determines whether the price you use on the product and invoices includes this tax.",
    )
    company_price_include = fields.Selection(
        selection=[("tax_included", "Tax Included"), ("tax_excluded", "Tax Excluded")],
        compute="_compute_company_price_include",
    )
    price_include_override = fields.Selection(
        selection=[("tax_included", "Tax Included"), ("tax_excluded", "Tax Excluded")],
        string="Included in Price",
        tracking=True,
        help="Overrides the Company's default on whether the price you use on "
        "the product and invoices includes this tax.",
    )
    include_base_amount = fields.Boolean(
        string="Affect Base of Subsequent Taxes",
        default=False,
        tracking=True,
        help="If set, taxes with a higher sequence than this one will be affected by it, provided they accept it.",
    )
    is_base_affected = fields.Boolean(
        string="Base Affected by Previous Taxes",
        default=True,
        tracking=True,
        help="If set, taxes with a lower sequence might affect this one, provided they try to do it.",
    )

    tax_group_id = fields.Many2one(
        comodel_name="account.tax.group",
        compute="_compute_tax_group_id",
        precompute=True,
        store=True,
        readonly=False,
        required=True,
        domain="[('country_id', 'in', (country_id, False))]",
    )
    invoice_repartition_line_ids = fields.One2many(
        comodel_name="account.tax.repartition.line",
        inverse_name="tax_id",
        string="Distribution for Invoices",
        compute="_compute_invoice_repartition_line_ids",
        store=True,
        readonly=False,
        domain=[("document_type", "=", "invoice")],
        help="Distribution when the tax is used on an invoice",
    )
    refund_repartition_line_ids = fields.One2many(
        comodel_name="account.tax.repartition.line",
        inverse_name="tax_id",
        string="Distribution for Refund Invoices",
        compute="_compute_refund_repartition_line_ids",
        store=True,
        readonly=False,
        domain=[("document_type", "=", "refund")],
        help="Distribution when the tax is used on a refund",
    )
    repartition_line_ids = fields.One2many(
        comodel_name="account.tax.repartition.line",
        inverse_name="tax_id",
        string="Distribution",
        copy=True,
    )

    country_id = fields.Many2one(
        comodel_name="res.country",
        compute="_compute_country_id",
        precompute=True,
        store=True,
        readonly=False,
        required=True,
        help="The country for which this tax is applicable.",
    )
    country_code = fields.Char(
        related="country_id.code",
        readonly=True,
    )

    has_negative_factor = fields.Boolean(compute="_compute_has_negative_factor")

    def _get_settings_company(self):
        return self.env.company

    def _serves_company(self, company):
        return company.id in self.sudo().company_ids.ids

    @api.constrains("company_ids")
    def _check_company_ids_not_empty(self):
        self.invalidate_recordset(fnames=["company_ids"])
        if taxes := self.filtered(lambda t: not t.sudo().company_ids):
            raise ValidationError(
                self.env._(
                    "The following taxes must be assigned to at least one "
                    "company:\n%(taxes)s",
                    taxes="\n".join(f"- {tax.display_name}" for tax in taxes),
                ),
            )

    @api.constrains("company_ids", "name", "type_tax_use", "tax_scope", "country_id")
    def _constrains_name(self):
        for taxes in map(self.browse, batched(self.ids, 100, strict=False)):
            domains = [
                [
                    ("company_ids", "in", tax.company_ids.ids),
                    ("name", "=", tax.name),
                    ("type_tax_use", "=", tax.type_tax_use),
                    ("tax_scope", "=", tax.tax_scope),
                    ("country_id", "=", tax.country_id.id),
                    ("id", "!=", tax.id),
                ]
                for tax in taxes
                if tax.type_tax_use != "none"
            ]
            if duplicates := self.sudo().search(Domain.OR(domains)):  # noqa: E8507 - one query per company; taxes sharing one were merged above
                raise ValidationError(
                    self.env._(
                        "Tax names must be unique!\n%(taxes)s",
                        taxes="\n".join(
                            self.env._(
                                "- %(name)s in %(company)s",
                                name=duplicate.name,
                                company=", ".join(duplicate.company_ids.mapped("name")),
                            )
                            for duplicate in duplicates
                        ),
                    ),
                )

    @api.constrains("tax_group_id")
    def _check_tax_group_id(self):
        for record in self:
            if (
                record.tax_group_id.country_id
                and record.tax_group_id.country_id != record.country_id
            ):
                raise ValidationError(
                    _(
                        "The tax group must have the same country_id as the tax using it."
                    )
                )

    @api.constrains(
        "invoice_repartition_line_ids",
        "refund_repartition_line_ids",
        "repartition_line_ids",
    )
    def _check_repartition_line_ids(self):
        for record in self:
            if (
                record.amount_type == "group"
                and not record.invoice_repartition_line_ids
                and not record.refund_repartition_line_ids
            ):
                continue

            invoice_repartition_line_ids = record.invoice_repartition_line_ids.sorted(
                lambda l: (l.sequence, l.id)
            )
            refund_repartition_line_ids = record.refund_repartition_line_ids.sorted(
                lambda l: (l.sequence, l.id)
            )
            record._check_repartition_lines(invoice_repartition_line_ids)
            record._check_repartition_lines(refund_repartition_line_ids)

            if len(invoice_repartition_line_ids) != len(refund_repartition_line_ids):
                raise ValidationError(
                    _(
                        "Invoice and credit note distribution should have the same number of lines."
                    )
                )

            if not invoice_repartition_line_ids.filtered(
                lambda x: x.repartition_type == "tax"
            ) or not refund_repartition_line_ids.filtered(
                lambda x: x.repartition_type == "tax"
            ):
                raise ValidationError(
                    _(
                        "Invoice and credit note repartition should have at least one tax repartition line."
                    )
                )

            index = 0
            while index < len(invoice_repartition_line_ids):
                inv_rep_ln = invoice_repartition_line_ids[index]
                ref_rep_ln = refund_repartition_line_ids[index]
                if (
                    inv_rep_ln.repartition_type != ref_rep_ln.repartition_type
                    or inv_rep_ln.factor_percent != ref_rep_ln.factor_percent
                ):
                    raise ValidationError(
                        _(
                            "Invoice and credit note distribution should match (same percentages, in the same order)."
                        )
                    )
                index += 1

            tax_reps = invoice_repartition_line_ids.filtered(
                lambda tax_rep: tax_rep.repartition_type == "tax"
            )
            total_pos_factor = sum(
                tax_reps.filtered(lambda tax_rep: tax_rep.factor > 0.0).mapped("factor")
            )
            if float_compare(total_pos_factor, 1.0, precision_digits=2):
                raise ValidationError(
                    _(
                        "Invoice and credit note distribution should have a total factor (+) equals to 100."
                    )
                )
            total_neg_factor = sum(
                tax_reps.filtered(lambda tax_rep: tax_rep.factor < 0.0).mapped("factor")
            )
            if total_neg_factor and float_compare(
                total_neg_factor, -1.0, precision_digits=2
            ):
                raise ValidationError(
                    _(
                        "Invoice and credit note distribution should have a total factor (-) equals to 100."
                    )
                )

    def _check_repartition_lines(self, lines):
        self.check_singleton()
        base_line = lines.filtered(lambda x: x.repartition_type == "base")
        if len(base_line) != 1:
            raise ValidationError(
                _(
                    "Invoice and credit note distribution should each contain exactly one line for the base."
                )
            )

    @api.constrains("children_tax_ids", "type_tax_use")
    def _check_children_scope(self):
        for tax in self:
            if tax._has_cycle("children_tax_ids"):
                raise ValidationError(_("Recursion found for tax “%s”.", tax.name))
            if any(
                child.type_tax_use not in ("none", tax.type_tax_use)
                or child.tax_scope not in (tax.tax_scope, False)
                for child in tax.children_tax_ids
            ):
                raise ValidationError(
                    _(
                        "The application scope of taxes in a group must be either the same as the group or left empty."
                    )
                )
            if any(child.amount_type == "group" for child in tax.children_tax_ids):
                raise ValidationError(_("Nested group of taxes are not allowed."))

    @api.model
    @api.readonly
    def name_search(self, name="", domain=None, operator="ilike", limit=100):
        return super().name_search(name, domain or Domain.TRUE, operator, limit)

    @staticmethod
    def _parse_name_search(name):
        regex = r"(\"[^\"]*\")"
        list_name = re.split(regex, name)
        for i, part in enumerate(list_name.copy()):
            if not part:
                continue
            if re.search(regex, part):
                list_name[i] = "%" + part.replace("%", "_").replace('"', "") + "%"
            else:
                list_name[i] = "%".join(re.sub(r"\W+", "", part))
        return "".join(list_name)

    @api.model
    def _search(self, domain, *args, **kwargs):
        def preprocess_name(cond):
            if (
                cond.field_expr in ("name", "display_name")
                and cond.operator in ("like", "ilike")
                and isinstance(cond.value, str)
            ):
                return Domain(
                    cond.field_expr,
                    cond.operator,
                    AccountTax._parse_name_search(cond.value),
                )
            return cond

        domain = Domain(domain).map_conditions(preprocess_name)
        return super()._search(domain, *args, **kwargs)

    @api.depends_context("company")
    def _compute_country_id(self):
        for tax in self:
            company = tax._get_settings_company()
            if "account_fiscal_country_id" in company._fields:
                tax.country_id = (
                    company.account_fiscal_country_id
                    or company.country_id
                    or tax.country_id
                )
            else:
                tax.country_id = company.country_id or tax.country_id

    @api.depends_context("company")
    @api.depends("country_id")
    def _compute_tax_group_id(self):
        company = self._get_settings_company()
        by_country = defaultdict(self.browse)
        for tax in self:
            if (
                not tax.tax_group_id
                or tax.tax_group_id.country_id != tax.country_id
                or company.id not in tax.tax_group_id.sudo().company_ids.ids
            ):
                by_country[tax.country_id] += tax
        for country, taxes in by_country.items():
            taxes.tax_group_id = self.env["account.tax.group"].search(  # noqa: E8507 - one lookup per country of the batch
                [
                    *self.env["account.tax.group"]._check_company_domain(company),
                    ("country_id", "=", country.id),
                ],
                limit=1,
            ) or self.env["account.tax.group"].search(  # noqa: E8507 - one lookup per country of the batch
                [
                    *self.env["account.tax.group"]._check_company_domain(company),
                    ("country_id", "=", False),
                ],
                limit=1,
            )

    @api.depends_context("company")
    def _compute_company_price_include(self):
        has_field = "account_price_include" in self.env["res.company"]._fields
        for tax in self:
            tax.company_price_include = (
                tax._get_settings_company().account_price_include
                if has_field
                else False
            )

    @api.depends("price_include_override")
    def _compute_price_include(self):
        for tax in self:
            tax.price_include = tax.price_include_override == "tax_included" or (
                tax.company_price_include == "tax_included"
                and not tax.price_include_override
            )

    def _search_price_include(self, operator, value):
        if operator not in ("in", "not in"):
            return NotImplemented
        if list(value) != [True]:
            raise ValueError(
                f"_search_price_include only supports boolean-normalized "
                f"domains, got {operator!r} {value!r}"
            )
        tax_value = "tax_included" if operator == "in" else "tax_excluded"
        if "account_price_include" not in self.env["res.company"]._fields:
            return [("price_include_override", "=", tax_value)]
        if self._get_settings_company().account_price_include == tax_value:
            return [
                "|",
                ("price_include_override", "=", tax_value),
                ("price_include_override", "=", False),
            ]
        return [("price_include_override", "=", tax_value)]

    @api.depends("company_ids")
    def _compute_invoice_repartition_line_ids(self):
        for tax in self:
            if not tax.invoice_repartition_line_ids:
                tax.invoice_repartition_line_ids = [
                    Command.create(
                        {"document_type": "invoice", "repartition_type": "base"}
                    ),
                    Command.create(
                        {"document_type": "invoice", "repartition_type": "tax"}
                    ),
                ]

    @api.depends("company_ids")
    def _compute_refund_repartition_line_ids(self):
        for tax in self:
            if not tax.refund_repartition_line_ids:
                tax.refund_repartition_line_ids = [
                    Command.create(
                        {"document_type": "refund", "repartition_type": "base"}
                    ),
                    Command.create(
                        {"document_type": "refund", "repartition_type": "tax"}
                    ),
                ]

    @api.depends(
        "invoice_repartition_line_ids.factor",
        "invoice_repartition_line_ids.repartition_type",
    )
    def _compute_has_negative_factor(self):
        for tax in self:
            tax_reps = tax.invoice_repartition_line_ids.filtered(
                lambda x: x.repartition_type == "tax"
            )
            tax.has_negative_factor = bool(
                tax_reps.filtered(lambda tax_rep: tax_rep.factor < 0.0)
            )

    @api.depends("type_tax_use", "tax_scope")
    @api.depends_context("append_fields", "formatted_display_name")
    def _compute_display_name(self):
        type_tax_uses = dict(
            self._fields["type_tax_use"]._description_selection(self.env)
        )
        scopes = dict(self._fields["tax_scope"]._description_selection(self.env))

        needs_markdown = self.env.context.get("formatted_display_name")
        wrapper = "\t--%s--" if needs_markdown else " (%s)"
        fields_to_include = set(self.env.context.get("append_fields") or [])

        for record in self:
            if name := record.name:
                if "type_tax_use" in fields_to_include and (
                    use := type_tax_uses.get(record.type_tax_use)
                ):
                    name += wrapper % use
                if "company_ids" in fields_to_include and len(self.env.companies) > 1:
                    name += wrapper % ", ".join(
                        record.company_ids.mapped("display_name")
                    )
                if needs_markdown and (scope := scopes.get(record.tax_scope)):
                    name += wrapper % scope
                branch = record._get_settings_company()._get_accessible_branches()[:1]
                fiscal_country = (
                    branch.account_fiscal_country_id
                    if "account_fiscal_country_id" in branch._fields
                    else branch.country_id
                )
                if record.country_id != fiscal_country:
                    name += wrapper % record.country_code

            record.display_name = name

    @api.depends("name", "invoice_label")
    def _compute_tax_label(self):
        for tax in self:
            tax.tax_label = tax.invoice_label or tax.name

    def _normalize_vals(self, vals):
        sanitized = vals.copy()

        if sanitized.get("description") and not re.search(
            r"<[^>]+>", sanitized["description"]
        ):
            sanitized["description"] = f"<div>{sanitized['description']}</div>"

        if "repartition_line_ids" in sanitized and (
            "invoice_repartition_line_ids" in sanitized
            or "refund_repartition_line_ids" in sanitized
        ):
            del sanitized["repartition_line_ids"]
        for doc_type in ("invoice", "refund"):
            fname = f"{doc_type}_repartition_line_ids"
            if fname not in sanitized:
                continue
            repartition = sanitized.setdefault("repartition_line_ids", [])
            for command_vals in sanitized.pop(fname):
                match command_vals[0]:
                    case Command.CREATE:
                        repartition.append(
                            Command.create(
                                {"document_type": doc_type, **command_vals[2]}
                            )
                        )
                    case Command.UPDATE:
                        repartition.append(
                            Command.update(
                                command_vals[1],
                                {"document_type": doc_type, **command_vals[2]},
                            )
                        )
                    case Command.CLEAR | Command.SET:
                        keep = (
                            set(command_vals[2])
                            if command_vals[0] == Command.SET
                            else set()
                        )
                        repartition.extend(
                            Command.delete(line.id)
                            for line in self.repartition_line_ids
                            if line.document_type == doc_type and line.id not in keep
                        )
                        repartition.extend(Command.link(line_id) for line_id in keep)
                    case _:
                        repartition.append(command_vals)
            sanitized[fname] = []
        return sanitized

    @api.model_create_multi
    def create(self, vals_list):
        context = clean_context(self.env.context)
        context.update(
            {
                "mail_create_nosubscribe": True,
                "mail_auto_subscribe_no_notify": True,
                "mail_create_nolog": True,
                "from_account_tax_creation": True,
            }
        )
        taxes = super(AccountTax, self.with_context(context)).create(
            [self._normalize_vals(vals) for vals in vals_list]
        )
        return taxes.with_context(self.env.context)

    def write(self, vals):
        return super().write(self._normalize_vals(vals))

    def copy_data(self, default=None):
        default = dict(default or {})
        vals_list = super().copy_data(default=default)
        if "name" not in default:
            for tax, vals in zip(self, vals_list, strict=True):
                vals["name"] = _("%s (copy)", tax.name)
        return vals_list

    def copy_translations(self, new, excluded=()):
        super().copy_translations(new, excluded=(*excluded, "name"))
        self._copy_translations_of_renamed_field(
            new, "name", lambda record, term: record.env._("%s (copy)", term)
        )

    @api.onchange("amount")
    def onchange_amount(self):
        if (
            self.amount_type in ("percent", "division")
            and not float_is_zero(self.amount, precision_digits=4)
            and not self.invoice_label
        ):
            self.invoice_label = f"{self.amount:.4g}%"

    @api.onchange("amount_type")
    def onchange_amount_type(self):
        if self.amount_type != "group":
            self.children_tax_ids = [Command.clear()]
        if self.amount_type == "group":
            self.invoice_label = None

    @api.onchange("price_include")
    def onchange_price_include(self):
        if self.price_include:
            self.include_base_amount = True

    def _eval_taxes_computation_prepare_product_fields(self):
        return set()

    @api.model
    def _eval_taxes_computation_prepare_product_default_values(self, field_names):
        default_value_map = {
            "integer": 0,
            "float": 0.0,
            "monetary": 0.0,
        }
        product_fields_values = {}
        for field_name in field_names:
            field = self.env["product.product"]._fields[field_name]
            product_fields_values[field_name] = {
                "type": field.type,
                "default_value": default_value_map[field.type],
            }
        return product_fields_values

    @api.model
    def _eval_taxes_computation_prepare_product_values(
        self, default_product_values, product=None
    ):
        product = product and product.sudo()
        product_values = {}
        for field_name, field_info in default_product_values.items():
            product_values[field_name] = (
                product and product[field_name]
            ) or field_info["default_value"]
        return product_values

    def _eval_taxes_computation_turn_to_product_values(self, product=None):
        product_fields = self._eval_taxes_computation_prepare_product_fields()
        default_product_values = (
            self._eval_taxes_computation_prepare_product_default_values(product_fields)
        )
        return self._eval_taxes_computation_prepare_product_values(
            default_product_values=default_product_values,
            product=product,
        )

    def _eval_taxes_computation_prepare_product_uom_fields(self):
        return set()

    @api.model
    def _eval_taxes_computation_prepare_product_uom_default_values(self, field_names):
        default_value_map = {
            "integer": 0,
            "float": 0.0,
            "monetary": 0.0,
        }
        product_uom_fields_values = {}
        for field_name in field_names:
            field = self.env["uom.uom"]._fields[field_name]
            product_uom_fields_values[field_name] = {
                "type": field.type,
                "default_value": default_value_map[field.type],
            }
        return product_uom_fields_values

    @api.model
    def _eval_taxes_computation_prepare_product_uom_values(
        self, default_product_uom_values, product_uom_id=None
    ):
        product_uom_id = product_uom_id and product_uom_id.sudo()
        product_uom_values = {}
        for field_name, field_info in default_product_uom_values.items():
            product_uom_values[field_name] = (
                product_uom_id and product_uom_id[field_name]
            ) or field_info["default_value"]
        return product_uom_values

    def _eval_taxes_computation_turn_to_product_uom_values(self, product_uom_id=None):
        product_uom_fields = self._eval_taxes_computation_prepare_product_uom_fields()
        default_product_uom_values = (
            self._eval_taxes_computation_prepare_product_uom_default_values(
                product_uom_fields
            )
        )
        return self._eval_taxes_computation_prepare_product_uom_values(
            default_product_uom_values=default_product_uom_values,
            product_uom_id=product_uom_id,
        )

    def _flatten_taxes_and_sort_them(self):
        def sort_key(tax):
            return tax.sequence, tax.id or None

        group_per_tax = {}
        sorted_taxes = self.env["account.tax"]
        for tax in self.sorted(key=sort_key):
            if tax.amount_type == "group":
                children = tax.children_tax_ids.sorted(key=sort_key)
                sorted_taxes |= children
                for child in children:
                    group_per_tax[child.id] = tax
            else:
                sorted_taxes |= tax
        return sorted_taxes, group_per_tax

    def _batch_for_taxes_computation(
        self, special_mode=False, filter_tax_function=None
    ):
        sorted_taxes, group_per_tax = self._flatten_taxes_and_sort_them()
        if filter_tax_function:
            sorted_taxes = sorted_taxes.filtered(filter_tax_function)

        results = {
            "batch_per_tax": {},
            "group_per_tax": group_per_tax,
            "sorted_taxes": sorted_taxes,
        }

        batch = self.env["account.tax"]
        is_base_affected = False
        for tax in reversed(results["sorted_taxes"]):
            if batch:
                same_batch = (
                    tax.amount_type == batch[0].amount_type
                    and (special_mode or tax.price_include == batch[0].price_include)
                    and tax.include_base_amount == batch[0].include_base_amount
                    and (
                        (tax.include_base_amount and not is_base_affected)
                        or not tax.include_base_amount
                    )
                )
                if not same_batch:
                    for batch_tax in batch:
                        results["batch_per_tax"][batch_tax.id] = batch
                    batch = self.env["account.tax"]

            is_base_affected = tax.is_base_affected
            batch |= tax

        if batch:
            for batch_tax in batch:
                results["batch_per_tax"][batch_tax.id] = batch
        return results

    def _propagate_extra_taxes_base(self, tax, taxes_data, special_mode=False):
        def get_tax_before():
            for tax_before in self:
                if tax_before in taxes_data[tax.id]["batch"]:
                    break
                yield tax_before

        def get_tax_after():
            for tax_after in reversed(list(self)):
                if tax_after in taxes_data[tax.id]["batch"]:
                    break
                yield tax_after

        def add_extra_base(other_tax, sign):
            tax_amount = taxes_data[tax.id]["tax_amount"]
            if "tax_amount" not in taxes_data[other_tax.id]:
                taxes_data[other_tax.id]["extra_base_for_tax"] += sign * tax_amount
            taxes_data[other_tax.id]["extra_base_for_base"] += sign * tax_amount

        if tax.price_include:
            if special_mode in (False, "total_included"):
                if tax.include_base_amount:
                    for other_tax in get_tax_after():
                        if not other_tax.is_base_affected:
                            add_extra_base(other_tax, -1)
                else:
                    for other_tax in get_tax_after():
                        add_extra_base(other_tax, -1)
                for other_tax in get_tax_before():
                    add_extra_base(other_tax, -1)

            elif tax.include_base_amount:
                for other_tax in get_tax_after():
                    if other_tax.is_base_affected:
                        add_extra_base(other_tax, 1)

        elif not tax.price_include:
            if special_mode in (False, "total_excluded"):
                if tax.include_base_amount:
                    for other_tax in get_tax_after():
                        if other_tax.is_base_affected:
                            add_extra_base(other_tax, 1)

            else:
                if not tax.include_base_amount:
                    for other_tax in get_tax_after():
                        add_extra_base(other_tax, -1)
                for other_tax in get_tax_before():
                    add_extra_base(other_tax, -1)

    def _eval_tax_amount_fixed_amount(self, batch, raw_base, evaluation_context):
        if self.amount_type == "fixed":
            sign = -1 if evaluation_context["price_unit"] < 0.0 else 1
            return sign * evaluation_context["quantity"] * self.amount
        return None

    def _eval_tax_amount_price_included(self, batch, raw_base, evaluation_context):
        self.check_singleton()
        if self.amount_type == "percent":
            total_percentage = sum(tax.amount for tax in batch) / 100.0
            to_price_excluded_factor = (
                1 / (1 + total_percentage)
                if float_compare(total_percentage, -1, precision_digits=10) != 0
                else 0.0
            )
            return raw_base * to_price_excluded_factor * self.amount / 100.0

        if self.amount_type == "division":
            return raw_base * self.amount / 100.0
        return None

    def _eval_tax_amount_price_excluded(self, batch, raw_base, evaluation_context):
        self.check_singleton()
        if self.amount_type == "percent":
            return raw_base * self.amount / 100.0

        if self.amount_type == "division":
            total_percentage = sum(tax.amount for tax in batch) / 100.0
            if float_compare(total_percentage, 1.0, precision_digits=10) > 0:
                raise ValidationError(
                    _(
                        "Division taxes applied together cannot exceed 100%% "
                        "(got %(total)s%%): it would leave a negative taxable base.",
                        total=round(total_percentage * 100.0, 4),
                    )
                )
            incl_base_multiplicator = (
                1.0
                if float_compare(total_percentage, 1.0, precision_digits=10) == 0
                else 1 - total_percentage
            )
            return raw_base * self.amount / 100.0 / incl_base_multiplicator
        return None

    def _get_tax_details(
        self,
        price_unit,
        quantity,
        precision_rounding=0.01,
        rounding_method="round_per_line",
        product=None,
        product_uom_id=None,
        special_mode=False,
        filter_tax_function=None,
    ):
        """Compute the tax amounts for ``self`` (the taxes to apply) against a
        single ``price_unit``/``quantity`` pair, in four passes over the
        taxes sorted by sequence/inclusion order (``_flatten_taxes_and_sort_them``,
        called earlier in the pipeline): fixed-amount taxes, price-included
        taxes, price-excluded taxes, then base-propagation (each tax's amount
        feeding the base of taxes that come after it, via
        ``_propagate_extra_taxes_base``). ``special_mode`` (``False``,
        ``"total_included"`` or ``"total_excluded"``) tells price-include
        resolution which of ``price_unit``'s two possible readings to assume
        when it is otherwise ambiguous. Taxes with a negative factor (reverse
        charge) get a mirrored, negated entry in ``reverse_charge_taxes_data``
        alongside their normal one in ``taxes_data``. ``total_excluded`` in the
        result is taken from the first entry of the sorted/batched tax list, an
        invariant depending on ``_batch_for_taxes_computation`` guaranteeing
        that first entry never has a base contribution from an earlier tax.
        """

        def add_tax_amount_to_results(tax, tax_amount):
            taxes_data[tax.id]["tax_amount"] = tax_amount
            if rounding_method == "round_per_line":
                taxes_data[tax.id]["tax_amount"] = float_round(
                    taxes_data[tax.id]["tax_amount"],
                    precision_rounding=precision_rounding,
                )
            if tax.has_negative_factor:
                reverse_charge_taxes_data[tax.id]["tax_amount"] = -taxes_data[tax.id][
                    "tax_amount"
                ]
            sorted_taxes._propagate_extra_taxes_base(
                tax, taxes_data, special_mode=special_mode
            )

        def eval_tax_amount(tax_amount_function, tax):
            is_already_computed = "tax_amount" in taxes_data[tax.id]
            if is_already_computed:
                return

            tax_amount = tax_amount_function(
                taxes_data[tax.id]["batch"],
                raw_base + taxes_data[tax.id]["extra_base_for_tax"],
                evaluation_context,
            )
            if tax_amount is not None:
                add_tax_amount_to_results(tax, tax_amount)

        def prepare_tax_extra_data(tax, **kwargs):
            if tax.has_negative_factor:
                price_include = False
            elif special_mode == "total_included":
                price_include = True
            elif special_mode == "total_excluded":
                price_include = False
            else:
                price_include = tax.price_include
            return {
                **kwargs,
                "tax": tax,
                "price_include": price_include,
                "extra_base_for_tax": 0.0,
                "extra_base_for_base": 0.0,
            }

        batching_results = self._batch_for_taxes_computation(
            special_mode=special_mode, filter_tax_function=filter_tax_function
        )
        sorted_taxes = batching_results["sorted_taxes"]
        taxes_data = {}
        reverse_charge_taxes_data = {}
        for tax in sorted_taxes:
            taxes_data[tax.id] = prepare_tax_extra_data(
                tax,
                group=batching_results["group_per_tax"].get(tax.id),
                batch=batching_results["batch_per_tax"][tax.id],
            )
            if tax.has_negative_factor:
                reverse_charge_taxes_data[tax.id] = {
                    **taxes_data[tax.id],
                    "is_reverse_charge": True,
                }

        raw_base = quantity * price_unit
        if rounding_method == "round_per_line":
            raw_base = float_round(raw_base, precision_rounding=precision_rounding)

        evaluation_context = {
            "product": sorted_taxes._eval_taxes_computation_turn_to_product_values(
                product=product
            ),
            "uom": sorted_taxes._eval_taxes_computation_turn_to_product_uom_values(
                product_uom_id=product_uom_id
            ),
            "price_unit": price_unit,
            "quantity": quantity,
            "raw_base": raw_base,
            "special_mode": special_mode,
        }

        for tax in reversed(sorted_taxes):
            eval_tax_amount(tax._eval_tax_amount_fixed_amount, tax)

        for tax in reversed(sorted_taxes):
            if taxes_data[tax.id]["price_include"]:
                eval_tax_amount(tax._eval_tax_amount_price_included, tax)

        for tax in sorted_taxes:
            if not taxes_data[tax.id]["price_include"]:
                eval_tax_amount(tax._eval_tax_amount_price_excluded, tax)

        subsequent_taxes = self.env["account.tax"]
        for tax in reversed(sorted_taxes):
            tax_data = taxes_data[tax.id]
            if "tax_amount" not in tax_data:
                continue

            total_tax_amount = sum(
                taxes_data[other_tax.id]["tax_amount"]
                for other_tax in tax_data["batch"]
            )
            total_tax_amount += sum(
                reverse_charge_taxes_data[other_tax.id]["tax_amount"]
                for other_tax in taxes_data[tax.id]["batch"]
                if other_tax.has_negative_factor
            )
            base = raw_base + tax_data["extra_base_for_base"]
            if tax_data["price_include"] and special_mode in (False, "total_included"):
                base -= total_tax_amount
            tax_data["base"] = base

            tax_data["taxes"] = self.env["account.tax"]
            if tax.include_base_amount:
                tax_data["taxes"] |= subsequent_taxes

            if tax.has_negative_factor:
                reverse_charge_tax_data = reverse_charge_taxes_data[tax.id]
                reverse_charge_tax_data["base"] = base
                reverse_charge_tax_data["taxes"] = tax_data["taxes"]

            if tax.is_base_affected:
                subsequent_taxes |= tax

        taxes_data_list = []
        for tax_data in taxes_data.values():
            if "tax_amount" in tax_data:
                taxes_data_list.append(tax_data)
                tax = tax_data["tax"]
                if tax.has_negative_factor:
                    taxes_data_list.append(reverse_charge_taxes_data[tax.id])

        if taxes_data_list:
            total_excluded = taxes_data_list[0]["base"]
            tax_amount = sum(tax_data["tax_amount"] for tax_data in taxes_data_list)
            total_included = total_excluded + tax_amount
        else:
            total_included = total_excluded = raw_base

        return {
            "total_excluded": total_excluded,
            "total_included": total_included,
            "taxes_data": [
                {
                    "tax": tax_data["tax"],
                    "taxes": tax_data["taxes"],
                    "group": batching_results["group_per_tax"].get(tax_data["tax"].id)
                    or self.env["account.tax"],
                    "batch": batching_results["batch_per_tax"][tax_data["tax"].id],
                    "tax_amount": tax_data["tax_amount"],
                    "price_include": tax_data["price_include"],
                    "base_amount": tax_data["base"],
                    "is_reverse_charge": tax_data.get("is_reverse_charge", False),
                }
                for tax_data in taxes_data_list
            ],
        }

    @api.model
    def _adapt_price_unit_to_another_taxes(
        self, price_unit, product, original_taxes, new_taxes, product_uom_id=None
    ):
        if original_taxes == new_taxes or False in original_taxes.mapped(
            "price_include"
        ):
            return price_unit

        taxes_computation = original_taxes._get_tax_details(
            price_unit,
            1.0,
            rounding_method="round_globally",
            product=product,
            product_uom_id=product_uom_id,
        )
        price_unit = taxes_computation["total_excluded"]

        taxes_computation = new_taxes._get_tax_details(
            price_unit,
            1.0,
            rounding_method="round_globally",
            product=product,
            product_uom_id=product_uom_id,
            special_mode="total_excluded",
        )
        delta = sum(
            x["tax_amount"]
            for x in taxes_computation["taxes_data"]
            if x["tax"].price_include
        )
        return price_unit + delta

    @api.model
    def _export_base_line_extra_tax_data(self, base_line):
        results = {}
        if base_line["computation_key"]:
            results["computation_key"] = base_line["computation_key"]

        store_source_data = False
        if base_line["manual_total_excluded_currency"] is not None:
            results["manual_total_excluded_currency"] = base_line[
                "manual_total_excluded_currency"
            ]
            store_source_data = True
        if base_line["manual_total_excluded"] is not None:
            results["manual_total_excluded"] = base_line["manual_total_excluded"]
            store_source_data = True
        if base_line["manual_tax_amounts"]:
            results["manual_tax_amounts"] = base_line["manual_tax_amounts"]
            store_source_data = True

        if store_source_data:
            results.update(
                {
                    "currency_id": base_line["currency_id"].id,
                    "price_unit": base_line["price_unit"],
                    "discount": base_line["discount"],
                    "quantity": base_line["quantity"],
                    "rate": base_line["rate"],
                }
            )
        return results

    @api.model
    def _import_base_line_extra_tax_data(self, base_line, extra_tax_data):
        results = {}
        if extra_tax_data and extra_tax_data.get("computation_key"):
            results["computation_key"] = extra_tax_data["computation_key"]

        manual_tax_amounts = (
            extra_tax_data.get("manual_tax_amounts") or {} if extra_tax_data else None
        )
        extra_tax_data_tax_ids = set(manual_tax_amounts or {})
        sorted_taxes = base_line["tax_ids"]._flatten_taxes_and_sort_them()[0]
        if (
            extra_tax_data
            and extra_tax_data.get("currency_id")
            and base_line["currency_id"].id == extra_tax_data["currency_id"]
            and base_line["currency_id"].compare_amounts(
                base_line["price_unit"], extra_tax_data["price_unit"]
            )
            == 0
            and base_line["currency_id"].compare_amounts(
                base_line["discount"], extra_tax_data["discount"]
            )
            == 0
            and base_line["currency_id"].compare_amounts(
                base_line["quantity"], extra_tax_data["quantity"]
            )
            == 0
            and len(sorted_taxes) == len(extra_tax_data_tax_ids)
            and all(str(tax.id) in extra_tax_data_tax_ids for tax in sorted_taxes)
        ):
            results["price_unit"] = extra_tax_data["price_unit"]

            if base_line["rate"] and extra_tax_data.get("rate"):
                delta_rate = base_line["rate"] / extra_tax_data["rate"]
            else:
                delta_rate = 1.0

            if "manual_total_excluded_currency" in extra_tax_data:
                results["manual_total_excluded_currency"] = extra_tax_data[
                    "manual_total_excluded_currency"
                ]
            if "manual_total_excluded" in extra_tax_data:
                results["manual_total_excluded"] = (
                    extra_tax_data["manual_total_excluded"] / delta_rate
                )

            if manual_tax_amounts:
                results["manual_tax_amounts"] = {}
                for tax_id_str, amounts in extra_tax_data["manual_tax_amounts"].items():
                    results["manual_tax_amounts"][tax_id_str] = dict(amounts)
                    if "tax_amount" in amounts:
                        results["manual_tax_amounts"][tax_id_str]["tax_amount"] /= (
                            delta_rate
                        )
                    if "base_amount" in amounts:
                        results["manual_tax_amounts"][tax_id_str]["base_amount"] /= (
                            delta_rate
                        )

        return results

    @api.model
    def _reverse_quantity_base_line_extra_tax_data(self, extra_tax_data):
        if not extra_tax_data:
            return None

        new_extra_tax_data = copy.deepcopy(extra_tax_data)
        for field in (
            "quantity",
            "manual_total_excluded_currency",
            "manual_total_excluded",
        ):
            if new_extra_tax_data.get(field):
                new_extra_tax_data[field] *= -1
        if new_extra_tax_data.get("manual_tax_amounts"):
            for current_manual_tax_amounts in new_extra_tax_data[
                "manual_tax_amounts"
            ].values():
                for suffix in ("_currency", ""):
                    for prefix in ("base", "tax"):
                        field = f"{prefix}_amount{suffix}"
                        if current_manual_tax_amounts.get(field):
                            current_manual_tax_amounts[field] *= -1
        return new_extra_tax_data

    def _turn_base_line_is_refund_flag_off(self, base_line):
        if not base_line["is_refund"]:
            return base_line

        new_base_line = {
            **base_line,
            "quantity": -base_line["quantity"],
            "is_refund": False,
        }
        tax_details = new_base_line["tax_details"]
        new_tax_details = new_base_line["tax_details"] = {
            f"{prefix}{field}{suffix}": -tax_details[f"{prefix}{field}{suffix}"]
            for prefix in ("raw_", "")
            for field in ("total_excluded", "total_included")
            for suffix in ("_currency", "")
        }
        for suffix in ("_currency", ""):
            field = f"delta_total_excluded{suffix}"
            new_tax_details[field] = -tax_details[field]

        new_tax_details["taxes_data"] = new_taxes_data = []
        for tax_data in tax_details["taxes_data"]:
            new_tax_data = {**tax_data}
            for prefix in ("raw_", ""):
                for suffix in ("_currency", ""):
                    for field in ("base_amount", "tax_amount"):
                        field = f"{prefix}{field}{suffix}"
                        new_tax_data[field] = -tax_data[field]
            new_taxes_data.append(new_tax_data)

        return new_base_line

    @api.model
    def _turn_base_lines_is_refund_flag_off(self, base_lines):
        return [
            self._turn_base_line_is_refund_flag_off(base_line)
            for base_line in base_lines
        ]

    @api.model
    def _get_base_line_field_value_from_record(
        self, record, field, extra_values, fallback, from_base_line=False
    ):
        need_origin = isinstance(fallback, models.Model)
        if field in extra_values:
            value = extra_values[field] or fallback
        elif (
            isinstance(record, models.Model)
            and field in record._fields
            and not from_base_line
        ):
            value = record[field]
        elif isinstance(record, dict):
            value = record.get(field, fallback)
        else:
            value = fallback
        if need_origin:
            value = value._origin
        return value

    @api.model
    def _prepare_base_line_for_taxes_computation(self, record, **kwargs):
        def load(field, fallback):
            return self._get_base_line_field_value_from_record(
                record, field, kwargs, fallback
            )

        currency = (
            load("currency_id", None)
            or load("company_currency_id", None)
            or load("company_id", self.env["res.company"]).currency_id
            or self.env["res.currency"]
        )

        base_line = {
            **kwargs,
            "record": record,
            "id": load("id", 0),
            "product_id": load("product_id", self.env["product.product"]),
            "product_uom_id": load("product_uom_id", self.env["uom.uom"]),
            "tax_ids": load("tax_ids", self.env["account.tax"]),
            "price_unit": load("price_unit", 0.0),
            "quantity": load("quantity", 0.0),
            "discount": load("discount", 0.0),
            "currency_id": currency,
            "special_mode": kwargs.get("special_mode") or False,
            "special_type": kwargs.get("special_type") or False,
            "rate": load("rate", 1.0),
            "filter_tax_function": kwargs.get("filter_tax_function") or None,
            "sign": load("sign", 1.0),
            "is_refund": load("is_refund", False),
            "partner_id": load("partner_id", self.env["res.partner"]),
            "account_id": load("account_id", False),
            "analytic_distribution": load("analytic_distribution", None),
        }

        extra_tax_data = self._import_base_line_extra_tax_data(
            base_line, load("extra_tax_data", {}) or {}
        )
        # NOTE: manual_total_excluded[_currency] use an explicit `is not None`
        # check, not `or` — 0.0 is a legitimate override (force the base to
        # zero) and must not be treated as absent, unlike `or`'s previous
        # behavior here which silently discarded it in favor of extra_tax_data.
        manual_total_excluded_currency = kwargs.get("manual_total_excluded_currency")
        if manual_total_excluded_currency is None:
            manual_total_excluded_currency = extra_tax_data.get(
                "manual_total_excluded_currency"
            )
        manual_total_excluded = kwargs.get("manual_total_excluded")
        if manual_total_excluded is None:
            manual_total_excluded = extra_tax_data.get("manual_total_excluded")
        base_line.update(
            {
                "computation_key": kwargs.get("computation_key")
                or extra_tax_data.get("computation_key"),
                "manual_total_excluded_currency": manual_total_excluded_currency,
                "manual_total_excluded": manual_total_excluded,
                "manual_tax_amounts": kwargs.get("manual_tax_amounts")
                or extra_tax_data.get("manual_tax_amounts"),
            }
        )
        if "price_unit" in extra_tax_data:
            base_line["price_unit"] = extra_tax_data["price_unit"]

        if record and isinstance(record, dict):
            for k, v in record.items():
                if k.startswith("_") and k not in base_line:
                    base_line[k] = v

        return base_line

    @api.model
    def _add_tax_details_in_base_line(self, base_line, company, rounding_method=None):
        rounding_method = rounding_method or (
            company.tax_calculation_rounding_method
            if "tax_calculation_rounding_method" in company._fields
            else "round_per_line"
        )
        price_unit_after_discount = base_line["price_unit"] * (
            1 - (base_line["discount"] / 100.0)
        )
        taxes_computation = base_line["tax_ids"]._get_tax_details(
            price_unit=price_unit_after_discount,
            quantity=base_line["quantity"],
            precision_rounding=base_line["currency_id"].rounding,
            rounding_method=rounding_method,
            product=base_line["product_id"],
            product_uom_id=base_line["product_uom_id"],
            special_mode=base_line["special_mode"],
            filter_tax_function=base_line["filter_tax_function"],
        )

        if base_line["special_type"] == "non_deductible":
            taxes_data = taxes_computation["taxes_data"]
            taxes_computation["taxes_data"] = []
            for tax_data in taxes_data:
                if not tax_data.get("is_reverse_charge"):
                    taxes_computation["taxes_data"].append(tax_data)
                else:
                    taxes_computation["total_included"] -= tax_data["tax_amount"]

        rate = base_line["rate"]
        tax_details = base_line["tax_details"] = {
            "raw_total_excluded_currency": taxes_computation["total_excluded"],
            "raw_total_excluded": taxes_computation["total_excluded"] / rate
            if rate
            else 0.0,
            "raw_total_included_currency": taxes_computation["total_included"],
            "raw_total_included": taxes_computation["total_included"] / rate
            if rate
            else 0.0,
            "taxes_data": [],
        }
        if rounding_method == "round_per_line":
            tax_details["raw_total_excluded"] = company.currency_id.round(
                tax_details["raw_total_excluded"]
            )
            tax_details["raw_total_included"] = company.currency_id.round(
                tax_details["raw_total_included"]
            )
        for tax_data in taxes_computation["taxes_data"]:
            tax_amount = tax_data["tax_amount"] / rate if rate else 0.0
            base_amount = tax_data["base_amount"] / rate if rate else 0.0
            if rounding_method == "round_per_line":
                tax_amount = company.currency_id.round(tax_amount)
                base_amount = company.currency_id.round(base_amount)
            tax_details["taxes_data"].append(
                {
                    **tax_data,
                    "raw_tax_amount_currency": tax_data["tax_amount"],
                    "raw_tax_amount": tax_amount,
                    "raw_base_amount_currency": tax_data["base_amount"],
                    "raw_base_amount": base_amount,
                }
            )

    @api.model
    def _add_tax_details_in_base_lines(self, base_lines, company):
        for base_line in base_lines:
            self._add_tax_details_in_base_line(base_line, company)

    @api.model
    def _normalize_target_factors(self, target_factors):
        factors = [
            (i, abs(target_factor["factor"]))
            for i, target_factor in enumerate(target_factors)
        ]
        factors.sort(key=lambda x: x[1], reverse=True)
        sum_of_factors = sum(x[1] for x in factors)
        return [
            (i, factor / sum_of_factors if sum_of_factors else 1 / len(factors))
            for i, factor in factors
        ]

    @api.model
    def _distribute_delta_amount_smoothly(
        self, precision_digits, delta_amount, target_factors
    ):
        """Spread ``delta_amount`` (a rounding residual) across ``target_factors``.

        Each entry of ``target_factors`` must be a dict exposing a ``"factor"``
        key; the residual is split proportionally to ``abs(factor)``, biggest
        factor first, with any leftover unit of precision (due to integer
        rounding of the split) assigned to the highest-weighted entries. The
        returned list always sums to exactly ``delta_amount`` at
        ``precision_digits``, regardless of the factors used — only *which*
        entries absorb the residual depends on the weights.

        Returns a list of deltas, one per ``target_factors`` entry, in the same
        order. With no targets, there is nothing to distribute onto: returns an
        all-empty list even for a non-zero ``delta_amount`` rather than
        raising, since a caller with an empty target list has no correction to
        apply.
        """
        precision_rounding = float(f"1e-{precision_digits}")
        amounts_to_distribute = [0.0] * len(target_factors)
        if not target_factors or float_is_zero(
            delta_amount, precision_digits=precision_digits
        ):
            return amounts_to_distribute

        sign = -1 if delta_amount < 0.0 else 1
        nb_of_errors = round(abs(delta_amount / precision_rounding))
        remaining_errors = nb_of_errors

        factors = self._normalize_target_factors(target_factors)
        for i, factor in factors:
            if not remaining_errors:
                break

            nb_of_amount_to_distribute = min(
                round(factor * nb_of_errors),
                remaining_errors,
            )
            remaining_errors -= nb_of_amount_to_distribute
            amount_to_distribute = (
                sign * nb_of_amount_to_distribute * precision_rounding
            )
            amounts_to_distribute[i] += amount_to_distribute

        for i in range(remaining_errors):
            amounts_to_distribute[factors[i][0]] += sign * precision_rounding

        return amounts_to_distribute

    @api.model
    def _round_tax_details_tax_amounts(self, base_lines, company, mode="mixed"):
        def grouping_function(base_line, tax_data):
            if not tax_data:
                return None
            return {
                "tax": tax_data["tax"],
                "currency": base_line["currency_id"],
                "is_refund": base_line["is_refund"],
                "is_reverse_charge": tax_data["is_reverse_charge"],
                "price_include": tax_data["price_include"],
                "computation_key": base_line["computation_key"],
            }

        base_lines_aggregated_values = self._aggregate_base_lines_tax_details(
            base_lines, grouping_function
        )
        values_per_grouping_key = self._aggregate_base_lines_aggregated_values(
            base_lines_aggregated_values
        )
        for grouping_key, values in values_per_grouping_key.items():
            if not grouping_key:
                continue

            price_include = grouping_key["price_include"]
            currency = grouping_key["currency"]
            for delta_currency_indicator, delta_currency in (
                ("_currency", currency),
                ("", company.currency_id),
            ):
                raw_total_tax_amount = values[
                    f"target_tax_amount{delta_currency_indicator}"
                ]
                rounded_raw_total_tax_amount = delta_currency.round(
                    raw_total_tax_amount
                )
                total_tax_amount = values[f"tax_amount{delta_currency_indicator}"]
                delta_total_tax_amount = rounded_raw_total_tax_amount - total_tax_amount

                if not delta_currency.is_zero(delta_total_tax_amount):
                    target_factors = [
                        {
                            "factor": tax_data[
                                f"raw_tax_amount{delta_currency_indicator}"
                            ],
                            "tax_data": tax_data,
                        }
                        for _base_line, taxes_data in values["base_line_x_taxes_data"]
                        for tax_data in taxes_data
                    ]
                    amounts_to_distribute = self._distribute_delta_amount_smoothly(
                        precision_digits=delta_currency.decimal_places,
                        delta_amount=delta_total_tax_amount,
                        target_factors=target_factors,
                    )
                    for target_factor, amount_to_distribute in zip(
                        target_factors, amounts_to_distribute, strict=True
                    ):
                        tax_data = target_factor["tax_data"]
                        tax_data[f"tax_amount{delta_currency_indicator}"] += (
                            amount_to_distribute
                        )

                raw_total_base_amount = values[
                    f"target_base_amount{delta_currency_indicator}"
                ]
                if (mode == "mixed" and price_include) or mode == "included":
                    raw_total_amount = raw_total_base_amount + raw_total_tax_amount
                    rounded_raw_total_amount = delta_currency.round(raw_total_amount)
                    total_amount = (
                        values[f"base_amount{delta_currency_indicator}"]
                        + total_tax_amount
                        + delta_total_tax_amount
                    )
                    delta_total_base_amount = rounded_raw_total_amount - total_amount
                elif (mode == "mixed" and not price_include) or mode == "excluded":
                    rounded_raw_total_base_amount = delta_currency.round(
                        raw_total_base_amount
                    )
                    total_base_amount = values[f"base_amount{delta_currency_indicator}"]
                    delta_total_base_amount = (
                        rounded_raw_total_base_amount - total_base_amount
                    )

                if not delta_currency.is_zero(delta_total_base_amount):
                    target_factors = [
                        {
                            "factor": tax_data[
                                f"raw_base_amount{delta_currency_indicator}"
                            ],
                            "tax_data": tax_data,
                        }
                        for _base_line, taxes_data in values["base_line_x_taxes_data"]
                        for tax_data in taxes_data
                    ]
                    amounts_to_distribute = self._distribute_delta_amount_smoothly(
                        precision_digits=delta_currency.decimal_places,
                        delta_amount=delta_total_base_amount,
                        target_factors=target_factors,
                    )
                    for target_factor, amount_to_distribute in zip(
                        target_factors, amounts_to_distribute, strict=True
                    ):
                        tax_data = target_factor["tax_data"]
                        tax_data[f"base_amount{delta_currency_indicator}"] += (
                            amount_to_distribute
                        )

    @api.model
    def _round_tax_details_base_lines(self, base_lines, company, mode="mixed"):
        def grouping_function(base_line, tax_data):
            return {
                "currency": base_line["currency_id"],
                "is_refund": base_line["is_refund"],
                "computation_key": base_line["computation_key"],
            }

        base_lines_aggregated_values = self._aggregate_base_lines_tax_details(
            base_lines, grouping_function
        )
        values_per_grouping_key = self._aggregate_base_lines_aggregated_values(
            base_lines_aggregated_values
        )
        for grouping_key, values in values_per_grouping_key.items():
            current_mode = mode
            if mode == "mixed":
                current_mode = "included"
                for base_line, taxes_data in values["base_line_x_taxes_data"]:
                    if any(
                        not tax_data["price_include"]
                        for tax_data in taxes_data
                        if (
                            not base_line["currency_id"].is_zero(
                                tax_data["tax_amount_currency"]
                            )
                            or not company.currency_id.is_zero(tax_data["tax_amount"])
                        )
                    ):
                        current_mode = "excluded"
                        break

            currency = grouping_key["currency"]
            for delta_currency_indicator, delta_currency in (
                ("_currency", currency),
                ("", company.currency_id),
            ):
                if current_mode == "excluded":
                    raw_total_excluded = values[
                        f"target_total_excluded{delta_currency_indicator}"
                    ]
                    if not raw_total_excluded:
                        continue

                    rounded_raw_total_excluded = delta_currency.round(
                        raw_total_excluded
                    )
                    total_excluded = values[f"total_excluded{delta_currency_indicator}"]
                    delta_total_excluded = rounded_raw_total_excluded - total_excluded
                    target_factors = [
                        {
                            "factor": base_line["tax_details"][
                                f"raw_total_excluded{delta_currency_indicator}"
                            ],
                            "base_line": base_line,
                        }
                        for base_line, _taxes_data in values["base_line_x_taxes_data"]
                    ]
                else:
                    raw_total_included = (
                        values[f"target_total_excluded{delta_currency_indicator}"]
                        + values[f"target_tax_amount{delta_currency_indicator}"]
                    )
                    if not raw_total_included:
                        continue

                    rounded_raw_total_included = delta_currency.round(
                        raw_total_included
                    )
                    total_included = (
                        values[f"total_excluded{delta_currency_indicator}"]
                        + values[f"tax_amount{delta_currency_indicator}"]
                    )
                    delta_total_excluded = rounded_raw_total_included - total_included
                    target_factors = [
                        {
                            "factor": base_line["tax_details"][
                                f"raw_total_included{delta_currency_indicator}"
                            ],
                            "base_line": base_line,
                        }
                        for base_line, _taxes_data in values["base_line_x_taxes_data"]
                    ]

                amounts_to_distribute = self._distribute_delta_amount_smoothly(
                    precision_digits=delta_currency.decimal_places,
                    delta_amount=delta_total_excluded,
                    target_factors=target_factors,
                )
                for target_factor, amount_to_distribute in zip(
                    target_factors, amounts_to_distribute, strict=True
                ):
                    base_line = target_factor["base_line"]
                    base_line["tax_details"][
                        f"delta_total_excluded{delta_currency_indicator}"
                    ] += amount_to_distribute

    @api.model
    def _round_tax_details_tax_amounts_from_tax_lines(
        self, base_lines, company, tax_lines
    ):
        if not tax_lines:
            return

        total_per_tax_line_key = defaultdict(
            lambda: {
                "currency": None,
                "tax_amount_currency": 0.0,
                "tax_amount": 0.0,
            }
        )
        for tax_line in tax_lines:
            tax_rep = tax_line["tax_repartition_line_id"]
            sign = tax_line["sign"]
            tax = tax_rep.tax_id
            currency = tax_line["currency_id"]
            tax_line_key = (tax.id, currency.id, tax_rep.document_type == "refund")
            total_per_tax_line_key[tax_line_key]["currency"] = currency
            total_per_tax_line_key[tax_line_key]["tax_amount_currency"] += (
                sign * tax_line["amount_currency"]
            )
            total_per_tax_line_key[tax_line_key]["tax_amount"] += (
                sign * tax_line["balance"]
            )

        def grouping_function(base_line, tax_data):
            if not tax_data:
                return None
            return {
                "tax": tax_data["tax"],
                "currency": base_line["currency_id"],
                "is_refund": base_line["is_refund"],
            }

        base_lines_aggregated_values = self._aggregate_base_lines_tax_details(
            base_lines, grouping_function
        )
        values_per_grouping_key = self._aggregate_base_lines_aggregated_values(
            base_lines_aggregated_values
        )
        for grouping_key, values in values_per_grouping_key.items():
            if not grouping_key:
                continue

            currency = grouping_key["currency"]
            tax_line_key = (
                grouping_key["tax"].id,
                currency.id,
                grouping_key["is_refund"],
            )
            if tax_line_key not in total_per_tax_line_key:
                continue

            for delta_currency_indicator, delta_currency in (
                ("_currency", currency),
                ("", company.currency_id),
            ):
                current_total_tax_amount = values[
                    f"tax_amount{delta_currency_indicator}"
                ]
                if not current_total_tax_amount:
                    continue

                target_total_tax_amount = total_per_tax_line_key[tax_line_key][
                    f"tax_amount{delta_currency_indicator}"
                ]
                delta_total_tax_amount = (
                    target_total_tax_amount - current_total_tax_amount
                )

                target_factors = [
                    {
                        "factor": tax_data[f"tax_amount{delta_currency_indicator}"],
                        "tax_data": tax_data,
                    }
                    for _base_line, taxes_data in values["base_line_x_taxes_data"]
                    for tax_data in taxes_data
                ]
                amounts_to_distribute = self._distribute_delta_amount_smoothly(
                    precision_digits=delta_currency.decimal_places,
                    delta_amount=delta_total_tax_amount,
                    target_factors=target_factors,
                )
                for target_factor, amount_to_distribute in zip(
                    target_factors, amounts_to_distribute, strict=True
                ):
                    tax_data = target_factor["tax_data"]
                    tax_data[f"tax_amount{delta_currency_indicator}"] += (
                        amount_to_distribute
                    )

    @api.model
    def _round_base_lines_tax_details(self, base_lines, company, tax_lines=None):
        for base_line in base_lines:
            tax_details = base_line["tax_details"]

            for suffix, currency in (
                ("_currency", base_line["currency_id"]),
                ("", company.currency_id),
            ):
                total_excluded_field = f"total_excluded{suffix}"
                tax_details[total_excluded_field] = currency.round(
                    tax_details[f"raw_{total_excluded_field}"]
                )

                for tax_data in tax_details["taxes_data"]:
                    for prefix in ("base", "tax"):
                        field = f"{prefix}_amount{suffix}"
                        tax_data[field] = currency.round(tax_data[f"raw_{field}"])

        for base_line in base_lines:
            manual_tax_amounts = base_line["manual_tax_amounts"]
            rate = base_line["rate"]
            tax_details = base_line["tax_details"]

            for suffix, currency in (
                ("_currency", base_line["currency_id"]),
                ("", company.currency_id),
            ):
                total_field = f"total_excluded{suffix}"
                manual_field = f"manual_{total_field}"
                if base_line[manual_field] is not None:
                    tax_details[total_field] = base_line[manual_field]
                    if suffix == "_currency" and rate:
                        tax_details["total_excluded"] = company.currency_id.round(
                            tax_details[total_field] / rate
                        )

                for tax_data in tax_details["taxes_data"]:
                    tax = tax_data["tax"]
                    reverse_charge_sign = -1 if tax_data["is_reverse_charge"] else 1
                    current_manual_tax_amounts = (
                        manual_tax_amounts and manual_tax_amounts.get(str(tax.id))
                    ) or {}
                    for prefix, factor in (("base", 1), ("tax", reverse_charge_sign)):
                        field = f"{prefix}_amount{suffix}"
                        if field in current_manual_tax_amounts:
                            tax_data[field] = currency.round(
                                factor * current_manual_tax_amounts[field]
                            )
                            if suffix == "_currency" and rate:
                                tax_data[f"{prefix}_amount"] = (
                                    company.currency_id.round(tax_data[field] / rate)
                                )

        for base_line in base_lines:
            tax_details = base_line["tax_details"]

            for suffix in ("_currency", ""):
                tax_details[f"delta_total_excluded{suffix}"] = 0.0
                tax_details[f"total_included{suffix}"] = tax_details[
                    f"total_excluded{suffix}"
                ]

                for tax_data in tax_details["taxes_data"]:
                    tax_details[f"total_included{suffix}"] += tax_data[
                        f"tax_amount{suffix}"
                    ]

        self._round_tax_details_tax_amounts(base_lines, company)
        self._round_tax_details_base_lines(base_lines, company)
        self._round_tax_details_tax_amounts_from_tax_lines(
            base_lines, company, tax_lines
        )

    @api.model
    def _aggregate_base_line_tax_details(self, base_line, grouping_function):
        values_per_grouping_key = {}
        tax_details = base_line["tax_details"]
        taxes_data = tax_details["taxes_data"]
        manual_tax_amounts = base_line["manual_tax_amounts"]

        for tax_data in taxes_data or [None]:
            current_manual_tax_amounts = (
                manual_tax_amounts
                and tax_data
                and manual_tax_amounts.get(str(tax_data["tax"].id))
            ) or {}

            grouping_key = grouping_function(base_line, tax_data)
            if isinstance(grouping_key, dict):
                grouping_key = frozendict(grouping_key)

            if grouping_key not in values_per_grouping_key:
                values = values_per_grouping_key[grouping_key] = {
                    "grouping_key": grouping_key,
                    "taxes_data": [],
                }
                for suffix in ("_currency", ""):
                    excluded_rounded_field = f"total_excluded{suffix}"
                    excluded_delta_field = f"delta_{excluded_rounded_field}"
                    excluded_raw_field = f"raw_{excluded_rounded_field}"
                    excluded_target_field = f"target_{excluded_rounded_field}"
                    excluded_manual_field = f"manual_{excluded_rounded_field}"
                    excluded_rounded_amount = (
                        tax_details[excluded_rounded_field]
                        + tax_details[excluded_delta_field]
                    )
                    excluded_raw_amount = tax_details[excluded_raw_field]
                    values[excluded_rounded_field] = excluded_rounded_amount
                    values[excluded_raw_field] = excluded_raw_amount
                    if base_line[excluded_manual_field] is not None:
                        excluded_target_amount = base_line[excluded_manual_field]
                    elif (
                        not suffix
                        and base_line["manual_total_excluded_currency"] is not None
                    ):
                        excluded_target_amount = excluded_rounded_amount
                    else:
                        excluded_target_amount = excluded_raw_amount
                    values[excluded_target_field] = excluded_target_amount

                    tax_base_rounded_field = f"base_amount{suffix}"
                    tax_base_raw_field = f"raw_{tax_base_rounded_field}"
                    tax_base_target_field = f"target_{tax_base_rounded_field}"
                    if tax_data:
                        values[tax_base_rounded_field] = tax_data[
                            tax_base_rounded_field
                        ]
                        values[tax_base_raw_field] = tax_data[tax_base_raw_field]
                        if tax_base_rounded_field in current_manual_tax_amounts:
                            values[tax_base_target_field] = current_manual_tax_amounts[
                                tax_base_rounded_field
                            ]
                        elif (
                            not suffix
                            and "base_amount_currency" in current_manual_tax_amounts
                        ):
                            values[tax_base_target_field] = tax_data[
                                tax_base_rounded_field
                            ]
                        else:
                            values[tax_base_target_field] = tax_data[tax_base_raw_field]
                    else:
                        values[tax_base_rounded_field] = excluded_rounded_amount
                        values[tax_base_raw_field] = excluded_raw_amount
                        values[tax_base_target_field] = excluded_target_amount

                    tax_rounded_field = f"tax_amount{suffix}"
                    tax_raw_field = f"raw_{tax_rounded_field}"
                    tax_target_field = f"target_{tax_rounded_field}"
                    values[tax_rounded_field] = 0.0
                    values[tax_raw_field] = 0.0
                    values[tax_target_field] = 0.0

            if tax_data:
                reverse_charge_sign = -1 if tax_data["is_reverse_charge"] else 1
                values = values_per_grouping_key[grouping_key]
                for suffix in ("_currency", ""):
                    tax_rounded_field = f"tax_amount{suffix}"
                    tax_raw_field = f"raw_{tax_rounded_field}"
                    tax_target_field = f"target_{tax_rounded_field}"
                    values[tax_rounded_field] += tax_data[tax_rounded_field]
                    values[tax_raw_field] += tax_data[tax_raw_field]
                    if tax_rounded_field in current_manual_tax_amounts:
                        values[tax_target_field] += (
                            reverse_charge_sign
                            * current_manual_tax_amounts[tax_rounded_field]
                        )
                    elif (
                        not suffix
                        and "tax_amount_currency" in current_manual_tax_amounts
                    ):
                        values[tax_target_field] = tax_data[tax_rounded_field]
                    else:
                        values[tax_target_field] += tax_data[tax_raw_field]
                values["taxes_data"].append(tax_data)

        return values_per_grouping_key

    @api.model
    def _aggregate_base_lines_tax_details(self, base_lines, grouping_function):
        return [
            (
                base_line,
                self._aggregate_base_line_tax_details(base_line, grouping_function),
            )
            for base_line in base_lines
        ]

    @api.model
    def _aggregate_base_lines_aggregated_values(self, base_lines_aggregated_values):
        default_float_fields = set()
        for prefix in ("", "raw_", "target_"):
            for suffix in ("_currency", ""):
                default_float_fields.update(
                    f"{prefix}{field}{suffix}"
                    for field in ("base_amount", "tax_amount", "total_excluded")
                )

        values_per_grouping_key = defaultdict(
            lambda: {
                **dict.fromkeys(default_float_fields, 0.0),
                "base_line_x_taxes_data": [],
            }
        )
        for base_line, aggregated_values in base_lines_aggregated_values:
            for grouping_key, values in aggregated_values.items():
                agg_values = values_per_grouping_key[grouping_key]
                for field in default_float_fields:
                    agg_values[field] += values[field]
                agg_values["grouping_key"] = grouping_key
                agg_values["base_line_x_taxes_data"].append(
                    (base_line, values["taxes_data"])
                )
        return values_per_grouping_key

    @api.model
    def _get_tax_totals_summary(
        self, base_lines, currency, company, cash_rounding=None
    ):
        tax_totals_summary = {
            "currency_id": currency.id,
            "currency_pd": currency.rounding,
            "company_currency_id": company.currency_id.id,
            "company_currency_pd": company.currency_id.rounding,
            "has_tax_groups": False,
            "subtotals": [],
            "base_amount_currency": 0.0,
            "base_amount": 0.0,
            "tax_amount_currency": 0.0,
            "tax_amount": 0.0,
        }

        def global_grouping_function(base_line, tax_data):
            return True if tax_data else None

        base_lines_aggregated_values = self._aggregate_base_lines_tax_details(
            base_lines, global_grouping_function
        )
        values_per_grouping_key = self._aggregate_base_lines_aggregated_values(
            base_lines_aggregated_values
        )
        for grouping_key, values in values_per_grouping_key.items():
            if grouping_key:
                tax_totals_summary["has_tax_groups"] = True
            tax_totals_summary["base_amount_currency"] += values[
                "total_excluded_currency"
            ]
            tax_totals_summary["base_amount"] += values["total_excluded"]
            tax_totals_summary["tax_amount_currency"] += values["tax_amount_currency"]
            tax_totals_summary["tax_amount"] += values["tax_amount"]

        untaxed_amount_subtotal_label = _("Untaxed Amount")
        subtotals = defaultdict(
            lambda: {
                "tax_groups": [],
                "tax_amount_currency": 0.0,
                "tax_amount": 0.0,
                "base_amount_currency": 0.0,
                "base_amount": 0.0,
            }
        )

        def tax_group_grouping_function(base_line, tax_data):
            return tax_data["tax"].tax_group_id if tax_data else None

        base_lines_aggregated_values = self._aggregate_base_lines_tax_details(
            base_lines, tax_group_grouping_function
        )
        values_per_grouping_key = self._aggregate_base_lines_aggregated_values(
            base_lines_aggregated_values
        )
        sorted_total_per_tax_group = sorted(
            [
                values
                for grouping_key, values in values_per_grouping_key.items()
                if grouping_key
            ],
            key=lambda values: (
                values["grouping_key"].sequence,
                values["grouping_key"].id,
            ),
        )

        encountered_base_amounts = set()
        subtotals_order = {}
        for order, values in enumerate(sorted_total_per_tax_group):
            tax_group = values["grouping_key"]

            involved_taxes = self.env["account.tax"]
            for _base_line, taxes_data in values["base_line_x_taxes_data"]:
                for tax_data in taxes_data:
                    involved_taxes |= tax_data["tax"]

            if set(involved_taxes.mapped("amount_type")) == {"fixed"}:
                display_base_amount = False
                display_base_amount_currency = False
            elif set(involved_taxes.mapped("amount_type")) == {"division"} and all(
                involved_taxes.mapped("price_include")
            ):
                display_base_amount = 0.0
                display_base_amount_currency = 0.0
                for base_line, _taxes_data in values["base_line_x_taxes_data"]:
                    tax_details = base_line["tax_details"]
                    display_base_amount += (
                        tax_details["total_excluded"]
                        + tax_details["delta_total_excluded"]
                    )
                    display_base_amount_currency += (
                        tax_details["total_excluded_currency"]
                        + tax_details["delta_total_excluded_currency"]
                    )
                    for tax_data in tax_details["taxes_data"]:
                        if tax_data["tax"].amount_type == "division":
                            display_base_amount_currency += tax_data[
                                "tax_amount_currency"
                            ]
                            display_base_amount += tax_data["tax_amount"]
            else:
                display_base_amount = values["base_amount"]
                display_base_amount_currency = values["base_amount_currency"]

            if display_base_amount_currency is not False:
                encountered_base_amounts.add(
                    float_repr(display_base_amount_currency, currency.decimal_places)
                )

            preceding_subtotal = (
                tax_group.preceding_subtotal or untaxed_amount_subtotal_label
            )
            if preceding_subtotal not in subtotals_order:
                subtotals_order[preceding_subtotal] = order

            subtotals[preceding_subtotal]["tax_groups"].append(
                {
                    "id": tax_group.id,
                    "involved_tax_ids": involved_taxes.ids,
                    "tax_amount_currency": values["tax_amount_currency"],
                    "tax_amount": values["tax_amount"],
                    "base_amount_currency": values["base_amount_currency"],
                    "base_amount": values["base_amount"],
                    "display_base_amount_currency": display_base_amount_currency,
                    "display_base_amount": display_base_amount,
                    "group_name": tax_group.name,
                    "group_label": tax_group.pos_receipt_label,
                }
            )

        if not subtotals:
            subtotals[untaxed_amount_subtotal_label]

        ordered_subtotals = sorted(
            subtotals.items(), key=lambda item: subtotals_order.get(item[0], 0)
        )
        accumulated_tax_amount_currency = 0.0
        accumulated_tax_amount = 0.0
        for subtotal_label, subtotal in ordered_subtotals:
            subtotal["name"] = subtotal_label
            subtotal["base_amount_currency"] = (
                tax_totals_summary["base_amount_currency"]
                + accumulated_tax_amount_currency
            )
            subtotal["base_amount"] = (
                tax_totals_summary["base_amount"] + accumulated_tax_amount
            )
            for tax_group in subtotal["tax_groups"]:
                subtotal["tax_amount_currency"] += tax_group["tax_amount_currency"]
                subtotal["tax_amount"] += tax_group["tax_amount"]
                accumulated_tax_amount_currency += tax_group["tax_amount_currency"]
                accumulated_tax_amount += tax_group["tax_amount"]
            tax_totals_summary["subtotals"].append(subtotal)

        cash_rounding_lines = [
            base_line
            for base_line in base_lines
            if base_line["special_type"] == "cash_rounding"
        ]
        if cash_rounding_lines:
            tax_totals_summary["cash_rounding_base_amount_currency"] = 0.0
            tax_totals_summary["cash_rounding_base_amount"] = 0.0
            for base_line in cash_rounding_lines:
                tax_details = base_line["tax_details"]
                tax_totals_summary["cash_rounding_base_amount_currency"] += tax_details[
                    "total_excluded_currency"
                ]
                tax_totals_summary["cash_rounding_base_amount"] += tax_details[
                    "total_excluded"
                ]
        elif cash_rounding:
            strategy = cash_rounding.strategy
            cash_rounding_pd = cash_rounding.rounding
            cash_rounding_method = cash_rounding.rounding_method
            total_amount_currency = (
                tax_totals_summary["base_amount_currency"]
                + tax_totals_summary["tax_amount_currency"]
            )
            total_amount = (
                tax_totals_summary["base_amount"] + tax_totals_summary["tax_amount"]
            )
            expected_total_amount_currency = float_round(
                total_amount_currency,
                precision_rounding=cash_rounding_pd,
                rounding_method=cash_rounding_method,
            )
            cash_rounding_base_amount_currency = (
                expected_total_amount_currency - total_amount_currency
            )
            rate = abs(total_amount_currency / total_amount) if total_amount else 0.0
            cash_rounding_base_amount = (
                company.currency_id.round(cash_rounding_base_amount_currency / rate)
                if rate
                else 0.0
            )
            if not currency.is_zero(cash_rounding_base_amount_currency):
                if strategy == "add_invoice_line":
                    tax_totals_summary["cash_rounding_base_amount_currency"] = (
                        cash_rounding_base_amount_currency
                    )
                    tax_totals_summary["cash_rounding_base_amount"] = (
                        cash_rounding_base_amount
                    )
                    tax_totals_summary["base_amount_currency"] += (
                        cash_rounding_base_amount_currency
                    )
                    tax_totals_summary["base_amount"] += cash_rounding_base_amount
                    subtotals[untaxed_amount_subtotal_label][
                        "base_amount_currency"
                    ] += cash_rounding_base_amount_currency
                    subtotals[untaxed_amount_subtotal_label]["base_amount"] += (
                        cash_rounding_base_amount
                    )
                elif strategy == "biggest_tax":
                    all_subtotal_tax_group = [
                        (subtotal, tax_group)
                        for subtotal in tax_totals_summary["subtotals"]
                        for tax_group in subtotal["tax_groups"]
                    ]

                    if all_subtotal_tax_group:
                        # Use abs(): on a credit note tax amounts are negative,
                        # and "biggest tax" must mean largest magnitude, not
                        # largest signed value.
                        max_subtotal, max_tax_group = max(
                            all_subtotal_tax_group,
                            key=lambda item: abs(item[1]["tax_amount_currency"]),
                        )
                        max_tax_group["tax_amount_currency"] += (
                            cash_rounding_base_amount_currency
                        )
                        max_tax_group["tax_amount"] += cash_rounding_base_amount
                        max_subtotal["tax_amount_currency"] += (
                            cash_rounding_base_amount_currency
                        )
                        max_subtotal["tax_amount"] += cash_rounding_base_amount
                        tax_totals_summary["tax_amount_currency"] += (
                            cash_rounding_base_amount_currency
                        )
                        tax_totals_summary["tax_amount"] += cash_rounding_base_amount
                    else:
                        cash_rounding_base_amount_currency = 0.0
                        cash_rounding_base_amount = 0.0

        cash_rounding_base_amount_currency = tax_totals_summary.get(
            "cash_rounding_base_amount_currency", 0.0
        )
        cash_rounding_base_amount = tax_totals_summary.get(
            "cash_rounding_base_amount", 0.0
        )
        tax_totals_summary["base_amount_currency"] -= cash_rounding_base_amount_currency
        tax_totals_summary["base_amount"] -= cash_rounding_base_amount
        for subtotal in tax_totals_summary["subtotals"]:
            subtotal["base_amount_currency"] -= cash_rounding_base_amount_currency
            subtotal["base_amount"] -= cash_rounding_base_amount
        encountered_base_amounts.add(
            float_repr(
                tax_totals_summary["base_amount_currency"], currency.decimal_places
            )
        )
        tax_totals_summary["same_tax_base"] = len(encountered_base_amounts) == 1

        taxed_non_deductible_lines = [
            base_line
            for base_line in base_lines
            if base_line["special_type"] == "non_deductible" and base_line["tax_ids"]
        ]
        if taxed_non_deductible_lines:
            base_lines_aggregated_values = self._aggregate_base_lines_tax_details(
                taxed_non_deductible_lines, tax_group_grouping_function
            )
            values_per_grouping_key = self._aggregate_base_lines_aggregated_values(
                base_lines_aggregated_values
            )
            for subtotal in tax_totals_summary["subtotals"]:
                for tax_group in subtotal["tax_groups"]:
                    tax_values = values_per_grouping_key[
                        self.env["account.tax.group"].browse(tax_group["id"])
                    ]
                    tax_group["non_deductible_tax_amount"] = tax_values["tax_amount"]
                    tax_group["non_deductible_tax_amount_currency"] = tax_values[
                        "tax_amount_currency"
                    ]

                    tax_group["tax_amount"] -= tax_values["tax_amount"]
                    tax_group["tax_amount_currency"] -= tax_values[
                        "tax_amount_currency"
                    ]
                    tax_group["base_amount"] -= tax_values["base_amount"]
                    tax_group["base_amount_currency"] -= tax_values[
                        "base_amount_currency"
                    ]

                    subtotal["tax_amount"] -= tax_values["tax_amount"]
                    subtotal["tax_amount_currency"] -= tax_values["tax_amount_currency"]

                    tax_totals_summary["tax_amount"] -= tax_values["tax_amount"]
                    tax_totals_summary["tax_amount_currency"] -= tax_values[
                        "tax_amount_currency"
                    ]

        tax_totals_summary["total_amount_currency"] = (
            tax_totals_summary["base_amount_currency"]
            + tax_totals_summary["tax_amount_currency"]
            + cash_rounding_base_amount_currency
        )
        tax_totals_summary["total_amount"] = (
            tax_totals_summary["base_amount"]
            + tax_totals_summary["tax_amount"]
            + cash_rounding_base_amount
        )

        return tax_totals_summary

    @api.model
    def _exclude_tax_groups_from_tax_totals_summary(self, tax_totals, ids_to_exclude):
        tax_totals = copy.deepcopy(tax_totals)
        ids_to_exclude = set(ids_to_exclude)

        subtotals = []
        for subtotal in tax_totals["subtotals"]:
            tax_groups = []
            for tax_group in subtotal["tax_groups"]:
                if tax_group["id"] in ids_to_exclude:
                    subtotal["base_amount_currency"] += tax_group["tax_amount_currency"]
                    subtotal["base_amount"] += tax_group["tax_amount"]
                    subtotal["tax_amount_currency"] -= tax_group["tax_amount_currency"]
                    subtotal["tax_amount"] -= tax_group["tax_amount"]
                    tax_totals["base_amount_currency"] += tax_group[
                        "tax_amount_currency"
                    ]
                    tax_totals["base_amount"] += tax_group["tax_amount"]
                    tax_totals["tax_amount_currency"] -= tax_group[
                        "tax_amount_currency"
                    ]
                    tax_totals["tax_amount"] -= tax_group["tax_amount"]
                else:
                    tax_groups.append(tax_group)

            if tax_groups:
                subtotal["tax_groups"] = tax_groups
                subtotals.append(subtotal)

        tax_totals["subtotals"] = subtotals
        return tax_totals

    def _can_be_discounted(self):
        self.check_singleton()
        return self.amount_type not in ("fixed", "code")

    @api.model
    def _get_undiscountable_filter(self, exclude_function=None):
        def dispatch_exclude_function(base_line, tax_data):
            return not tax_data["tax"]._can_be_discounted() or (
                exclude_function is not None and exclude_function(base_line, tax_data)
            )

        return dispatch_exclude_function

    @api.model
    def _partition_base_lines_taxes(self, base_lines, partition_function):
        has_taxes_to_exclude = False
        base_lines_partition_taxes = []
        for base_line in base_lines:
            tax_details = base_line["tax_details"]
            taxes_data = tax_details["taxes_data"]
            taxes_to_keep = self.env["account.tax"]
            taxes_to_exclude = self.env["account.tax"]
            for tax_data in taxes_data:
                if partition_function(base_line, tax_data):
                    taxes_to_keep += tax_data["tax"]
                else:
                    taxes_to_exclude += tax_data["tax"]
            if taxes_to_exclude:
                has_taxes_to_exclude = True
            base_lines_partition_taxes.append(
                (base_line, taxes_to_keep, taxes_to_exclude)
            )
        return base_lines_partition_taxes, has_taxes_to_exclude

    @api.model
    def _merge_tax_details(self, tax_details_1, tax_details_2):
        results = {
            f"{prefix}{field}{suffix}": tax_details_1[f"{prefix}{field}{suffix}"]
            + tax_details_2[f"{prefix}{field}{suffix}"]
            for prefix in ("raw_", "")
            for field in ("total_excluded", "total_included")
            for suffix in ("_currency", "")
        }
        for suffix in ("_currency", ""):
            field = f"delta_total_excluded{suffix}"
            results[field] = tax_details_1[field] + tax_details_2[field]

        agg_taxes_data = {}
        for tax_details in (tax_details_1, tax_details_2):
            for tax_data in tax_details["taxes_data"]:
                tax = tax_data["tax"]
                if tax in agg_taxes_data:
                    agg_tax_data = agg_taxes_data[tax]
                    for prefix in ("raw_", ""):
                        for suffix in ("_currency", ""):
                            for field in ("base_amount", "tax_amount"):
                                field_with_prefix = f"{prefix}{field}{suffix}"
                                agg_tax_data[field_with_prefix] += tax_data[
                                    field_with_prefix
                                ]
                else:
                    agg_taxes_data[tax] = dict(tax_data)
        results["taxes_data"] = list(agg_taxes_data.values())

        taxes_in_2 = {tax_data["tax"] for tax_data in tax_details_2["taxes_data"]}
        taxes_only_in_1 = {
            tax_data["tax"]
            for tax_data in tax_details_1["taxes_data"]
            if tax_data["tax"] not in taxes_in_2
        }
        for tax_data in results["taxes_data"]:
            if tax_data["tax"] in taxes_only_in_1:
                for suffix in ("_currency", ""):
                    for prefix in ("raw_", ""):
                        tax_data[f"{prefix}base_amount{suffix}"] += tax_details_2[
                            f"{prefix}total_excluded{suffix}"
                        ]
                    tax_data[f"base_amount{suffix}"] += tax_details_2[
                        f"delta_total_excluded{suffix}"
                    ]

        return results

    @api.model
    def _add_tax_data_to_included_totals(self, tax_details, tax_data):
        for suffix in ("_currency", ""):
            tax_details[f"raw_total_included{suffix}"] += tax_data[
                f"raw_tax_amount{suffix}"
            ]
            tax_details[f"total_included{suffix}"] += tax_data[f"tax_amount{suffix}"]

    @api.model
    def _split_tax_data(self, base_line, tax_data, company, target_factors):
        """Split one tax_data entry proportionally across ``target_factors``
        (each a dict with a ``"factor"`` key, normalized internally so they
        need not sum to 1). Returns a new list of tax_data dicts, one per
        factor, in the same order as ``target_factors``. Raw amounts are
        scaled by the factor directly; the rounded ``*_amount``/``*_amount_currency``
        fields are re-derived via ``_distribute_delta_amount_smoothly`` so the
        split parts still sum back to the original ``tax_data``'s rounded
        totals despite each part being rounded independently.
        """
        currency = base_line["currency_id"]

        factors = self._normalize_target_factors(target_factors)

        new_taxes_data = [None] * len(factors)

        for index, factor in factors:
            new_taxes_data[index] = {
                **tax_data,
                "raw_tax_amount_currency": factor * tax_data["raw_tax_amount_currency"],
                "raw_tax_amount": factor * tax_data["raw_tax_amount"],
                "raw_base_amount_currency": factor
                * tax_data["raw_base_amount_currency"],
                "raw_base_amount": factor * tax_data["raw_base_amount"],
            }

        new_target_factors = [
            {
                "factor": target_factor["factor"],
                "tax_data": new_tax_data,
            }
            for new_tax_data, target_factor in zip(
                new_taxes_data, target_factors, strict=True
            )
        ]

        for delta_currency_indicator, delta_currency in (
            ("_currency", currency),
            ("", company.currency_id),
        ):
            for prefix in ("tax", "base"):
                field = f"{prefix}_amount{delta_currency_indicator}"
                amounts_to_distribute = self._distribute_delta_amount_smoothly(
                    precision_digits=delta_currency.decimal_places,
                    delta_amount=tax_data[field],
                    target_factors=new_target_factors,
                )
                for target_factor, amount_to_distribute in zip(
                    new_target_factors, amounts_to_distribute, strict=True
                ):
                    new_tax_data = target_factor["tax_data"]
                    new_tax_data[field] = amount_to_distribute
        return new_taxes_data

    @api.model
    def _split_tax_details(self, base_line, company, target_factors):
        """Split ``base_line["tax_details"]`` (totals + all its taxes_data)
        proportionally across ``target_factors``, calling ``_split_tax_data``
        per tax and re-deriving ``total_excluded``/``total_included`` for each
        part the same rounded-yet-sum-preserving way. Returns a new list of
        tax_details dicts, one per factor, in ``target_factors`` order.
        """
        currency = base_line["currency_id"]
        tax_details = base_line["tax_details"]

        factors = self._normalize_target_factors(target_factors)

        new_tax_details_list = [None] * len(factors)

        for index, factor in factors:
            new_tax_details_list[index] = {
                "raw_total_excluded_currency": factor
                * tax_details["raw_total_excluded_currency"],
                "raw_total_excluded": factor * tax_details["raw_total_excluded"],
                "raw_total_included_currency": factor
                * tax_details["raw_total_included_currency"],
                "raw_total_included": factor * tax_details["raw_total_included"],
                "delta_total_excluded_currency": 0.0,
                "delta_total_excluded": 0.0,
                "taxes_data": [],
            }

        for tax_data in tax_details["taxes_data"]:
            new_taxes_data = self._split_tax_data(
                base_line, tax_data, company, target_factors
            )
            for new_tax_details, new_tax_data in zip(
                new_tax_details_list, new_taxes_data, strict=True
            ):
                new_tax_details["taxes_data"].append(new_tax_data)

        for delta_currency_indicator, delta_currency in (
            ("_currency", currency),
            ("", company.currency_id),
        ):
            new_target_factors = [
                {
                    "factor": new_tax_details[
                        f"raw_total_excluded{delta_currency_indicator}"
                    ],
                    "tax_details": new_tax_details,
                }
                for new_tax_details in new_tax_details_list
            ]
            field = f"total_excluded{delta_currency_indicator}"
            delta_amount = tax_details[field]
            amounts_to_distribute = self._distribute_delta_amount_smoothly(
                precision_digits=delta_currency.decimal_places,
                delta_amount=delta_amount,
                target_factors=new_target_factors,
            )
            for target_factor, amount_to_distribute in zip(
                new_target_factors, amounts_to_distribute, strict=True
            ):
                new_tax_details = target_factor["tax_details"]
                new_tax_details[field] = amount_to_distribute

        for new_tax_details in new_tax_details_list:
            for delta_currency_indicator in ("_currency", ""):
                new_tax_details[f"total_included{delta_currency_indicator}"] = (
                    new_tax_details[f"total_excluded{delta_currency_indicator}"]
                    + sum(
                        new_tax_data[f"tax_amount{delta_currency_indicator}"]
                        for new_tax_data in new_tax_details["taxes_data"]
                    )
                )
        return new_tax_details_list

    @api.model
    def _split_base_line(self, base_line, company, target_factors, update_kwargs=None):
        """Split ``base_line`` (``price_unit`` and ``tax_details``) proportionally
        across ``target_factors``, returning one new base line per factor via
        ``_prepare_base_line_for_taxes_computation``. ``update_kwargs(base_line,
        target_factor, kwargs)``, if given, is called per split part to add or
        override extra kwargs (e.g. a caller-specific ``quantity``) before the
        new base line is built.
        """
        factors = self._normalize_target_factors(target_factors)

        new_tax_details_list = self._split_tax_details(
            base_line, company, target_factors
        )

        new_base_lines = [None] * len(factors)
        for index, factor in factors:
            kwargs = {
                "price_unit": factor * base_line["price_unit"],
                "tax_details": new_tax_details_list[index],
            }
            if update_kwargs:
                update_kwargs(base_line, target_factors[index], kwargs)
            new_base_lines[index] = self._prepare_base_line_for_taxes_computation(
                base_line, **kwargs
            )
        return new_base_lines

    @api.model
    def _dispatch_taxes_into_new_base_lines(
        self, base_lines, company, exclude_function
    ):
        """Peel taxes matched by ``exclude_function(base_line, tax_data)`` off
        of ``base_lines`` and into their own new base lines, so that the
        original lines keep only the taxes ``exclude_function`` did not match
        (used e.g. to isolate discount-ineligible taxes onto a separate line).
        Processes a work queue (``to_process``) of (index, base_line,
        taxes_to_exclude) tuples so a base line with several excluded taxes is
        peeled one tax at a time rather than all at once. Returns the flat
        list of newly created base lines (the untouched originals are mutated
        in place and are not part of the return value).
        """

        def partition_function(base_line, tax_data):
            return not exclude_function(base_line, tax_data)

        base_lines_partition_taxes = self._partition_base_lines_taxes(
            base_lines, partition_function
        )[0]
        new_base_lines_list = [[] for _base_line in base_lines]
        to_process = deque(
            (index, base_line, taxes_to_exclude)
            for index, (base_line, _taxes_to_keep, taxes_to_exclude) in enumerate(
                base_lines_partition_taxes
            )
        )
        while to_process:
            index, base_line, taxes_to_exclude = to_process.popleft()

            tax_details = base_line["tax_details"]
            taxes_data = tax_details["taxes_data"]

            next_split_index = None
            for i, tax_data in enumerate(taxes_data):
                if tax_data["tax"] in taxes_to_exclude:
                    next_split_index = i
                    break

            if next_split_index is None:
                new_base_lines_list[index].append(dict(base_line))
                continue

            common_taxes_data = taxes_data[:next_split_index]
            tax_data_to_remove = taxes_data[next_split_index]
            remaining_taxes_data = taxes_data[next_split_index + 1 :]

            first_tax_details = {
                k: tax_details[k]
                for k in (
                    "raw_total_excluded_currency",
                    "raw_total_excluded",
                    "total_excluded_currency",
                    "total_excluded",
                    "delta_total_excluded_currency",
                    "delta_total_excluded",
                )
            }
            first_tax_details["taxes_data"] = common_taxes_data
            for suffix in ("_currency", ""):
                first_tax_details[f"raw_total_included{suffix}"] = first_tax_details[
                    f"raw_total_excluded{suffix}"
                ] + sum(
                    common_tax_data[f"raw_tax_amount{suffix}"]
                    for common_tax_data in common_taxes_data
                )
                first_tax_details[f"total_included{suffix}"] = (
                    first_tax_details[f"total_excluded{suffix}"]
                    + first_tax_details[f"delta_total_excluded{suffix}"]
                    + sum(
                        common_tax_data[f"tax_amount{suffix}"]
                        for common_tax_data in common_taxes_data
                    )
                )
            second_tax_details = {
                "raw_total_excluded_currency": tax_data_to_remove[
                    "raw_tax_amount_currency"
                ],
                "raw_total_excluded": tax_data_to_remove["raw_tax_amount"],
                "total_excluded_currency": tax_data_to_remove["tax_amount_currency"],
                "total_excluded": tax_data_to_remove["tax_amount"],
                "delta_total_excluded_currency": 0.0,
                "delta_total_excluded": 0.0,
                "raw_total_included_currency": tax_data_to_remove[
                    "raw_tax_amount_currency"
                ],
                "raw_total_included": tax_data_to_remove["raw_tax_amount"],
                "total_included_currency": tax_data_to_remove["tax_amount_currency"],
                "total_included": tax_data_to_remove["tax_amount"],
                "taxes_data": [],
            }

            target_factors = [
                {
                    "factor": first_tax_details["raw_total_excluded_currency"],
                    "tax_details": first_tax_details,
                },
                {
                    "factor": second_tax_details["raw_total_excluded_currency"],
                    "tax_details": second_tax_details,
                },
            ]
            for remaining_tax_data in remaining_taxes_data:
                if remaining_tax_data["tax"] in tax_data_to_remove["taxes"]:
                    new_remaining_taxes_data = self._split_tax_data(
                        base_line, remaining_tax_data, company, target_factors
                    )

                    first_tax_data = new_remaining_taxes_data[0]

                    second_tax_details["taxes_data"].append(new_remaining_taxes_data[1])
                    self._add_tax_data_to_included_totals(
                        second_tax_details, new_remaining_taxes_data[1]
                    )
                else:
                    first_tax_data = remaining_tax_data

                first_tax_details["taxes_data"].append(first_tax_data)
                self._add_tax_data_to_included_totals(first_tax_details, first_tax_data)

            first_taxes = self.env["account.tax"]
            for tax_data in first_tax_details["taxes_data"]:
                first_taxes += tax_data["tax"]
            first_base_line = self._prepare_base_line_for_taxes_computation(
                base_line,
                tax_ids=first_taxes,
                tax_details=first_tax_details,
            )

            second_taxes = self.env["account.tax"]
            for tax_data in second_tax_details["taxes_data"]:
                second_taxes += tax_data["tax"]
            second_base_line = self._prepare_base_line_for_taxes_computation(
                base_line,
                tax_ids=second_taxes,
                price_unit=(
                    second_tax_details["raw_total_excluded_currency"]
                    + sum(
                        sub_tax_data["raw_tax_amount_currency"]
                        for sub_tax_data in second_tax_details["taxes_data"]
                        if sub_tax_data["tax"].price_include
                    )
                )
                / (base_line["quantity"] or 1.0),
                tax_details=second_tax_details,
                _removed_tax_data=tax_data_to_remove,
            )
            to_process.appendleft((index, second_base_line, taxes_to_exclude))
            to_process.appendleft((index, first_base_line, taxes_to_exclude))

        final_base_lines = []
        for new_base_lines in new_base_lines_list:
            new_base_lines[0]["removed_taxes_data_base_lines"] = new_base_lines[1:]
            final_base_lines.append(new_base_lines[0])
        return final_base_lines

    @api.model
    def _turn_removed_taxes_into_new_base_lines(
        self, base_lines, company, grouping_function=None, aggregate_function=None
    ):
        extra_base_lines = []
        for base_line in base_lines:
            extra_base_lines += base_line["removed_taxes_data_base_lines"]
        return self._reduce_base_lines_with_grouping_function(
            base_lines=extra_base_lines,
            grouping_function=grouping_function,
            aggregate_function=aggregate_function,
        )

    @api.model
    def _reduce_base_lines_with_grouping_function(
        self,
        base_lines,
        grouping_function=None,
        aggregate_function=None,
        computation_key=None,
    ):
        aggregated_base_lines = {}
        base_line_map = {}
        for base_line in base_lines:
            price_unit_after_discount = base_line["price_unit"] * (
                1 - (base_line["discount"] / 100.0)
            )
            new_base_line = self._prepare_base_line_for_taxes_computation(
                base_line,
                price_unit=base_line["quantity"] * price_unit_after_discount,
                quantity=1.0,
                discount=0.0,
            )
            grouping_key = {"tax_ids": new_base_line["tax_ids"]}
            if grouping_function:
                grouping_key.update(grouping_function(new_base_line))
            grouping_key = frozendict(grouping_key)

            target_base_line = base_line_map.get(grouping_key)
            if target_base_line:
                target_base_line["price_unit"] += new_base_line["price_unit"]
                target_base_line["tax_details"] = self._merge_tax_details(
                    tax_details_1=target_base_line["tax_details"],
                    tax_details_2=base_line["tax_details"],
                )
            else:
                target_base_line = self._prepare_base_line_for_taxes_computation(
                    new_base_line,
                    **grouping_key,
                    computation_key=computation_key,
                    tax_details={
                        **base_line["tax_details"],
                        "taxes_data": [
                            dict(tax_data)
                            for tax_data in base_line["tax_details"]["taxes_data"]
                        ],
                    },
                )
                base_line_map[grouping_key] = target_base_line

            if aggregate_function:
                aggregate_function(target_base_line, base_line)
            aggregated_base_lines.setdefault(grouping_key, []).append(base_line)

        base_line_map = {
            grouping_key: base_line
            for grouping_key, base_line in base_line_map.items()
            if not base_line["currency_id"].is_zero(base_line["price_unit"])
        }

        for grouping_key, base_line in base_line_map.items():
            total_factor = 0.0
            analytic_distribution_to_aggregate = defaultdict(float)
            for aggregated_base_line in aggregated_base_lines[grouping_key]:
                amount = aggregated_base_line["tax_details"][
                    "raw_total_excluded_currency"
                ]
                total_factor += amount
                for account_id, distribution in (
                    aggregated_base_line["analytic_distribution"] or {}
                ).items():
                    analytic_distribution_to_aggregate[account_id] += (
                        distribution * amount / 100.0
                    )
            analytic_distribution = {}
            for account_id, amount in analytic_distribution_to_aggregate.items():
                analytic_distribution[account_id] = (
                    amount * 100 / total_factor if total_factor else 0.0
                )
            base_line["analytic_distribution"] = analytic_distribution

        return list(base_line_map.values())

    @api.model
    def _reduce_base_lines_to_target_amount(
        self,
        base_lines,
        company,
        amount_type,
        amount,
        computation_key=None,
        grouping_function=None,
        aggregate_function=None,
    ):
        """Rescale ``base_lines`` (e.g. a discount/down-payment's own generated
        lines) so their combined total hits ``amount`` exactly: either a
        ``"fixed"`` target amount, or a ``"percentage"`` of the lines'
        current total. Rescales each line's ``price_unit`` proportionally,
        recomputes tax details from scratch on the rescaled lines, then
        distributes the residual per-tax rounding delta via
        ``_spread_delta_on_base_amount`` so the recomputed totals land on the
        target exactly rather than merely close to it.
        """
        if not base_lines:
            return []

        currency = base_lines[0]["currency_id"]
        rate = base_lines[0]["rate"]

        total_amount_currency, total_amount = self._measure_base_lines_total(base_lines)

        tax_amounts_per_tax = self._measure_tax_amounts_per_tax(base_lines)

        sign = -1 if amount < 0.0 else 1
        signed_amount = sign * amount
        if amount_type == "fixed":
            percentage = (
                (signed_amount / total_amount_currency)
                if total_amount_currency
                else 0.0
            )
            expected_total_amount_currency = currency.round(amount)
            expected_total_amount = (
                company.currency_id.round(expected_total_amount_currency / rate)
                if rate
                else 0.0
            )
        else:
            percentage = signed_amount / 100.0
            expected_total_amount_currency = currency.round(
                total_amount_currency * sign * percentage
            )
            expected_total_amount = company.currency_id.round(
                total_amount * sign * percentage
            )

        expected_tax_amounts = {
            grouping_key: {
                "tax_amount_currency": currency.round(
                    values["tax_amount_currency"] * sign * percentage
                ),
                "tax_amount": company.currency_id.round(
                    values["tax_amount"] * sign * percentage
                ),
                "base_amount_currency": currency.round(
                    values["base_amount_currency"] * sign * percentage
                ),
                "base_amount": company.currency_id.round(
                    values["base_amount"] * sign * percentage
                ),
            }
            for grouping_key, values in tax_amounts_per_tax.items()
        }
        expected_base_amount_currency = expected_total_amount_currency - sum(
            values["tax_amount_currency"] for values in expected_tax_amounts.values()
        )
        expected_base_amount = expected_total_amount - sum(
            values["tax_amount"] for values in expected_tax_amounts.values()
        )

        reduced_base_lines = self._reduce_base_lines_with_grouping_function(
            base_lines=base_lines,
            grouping_function=grouping_function,
            aggregate_function=aggregate_function,
            computation_key=computation_key,
        )
        if not reduced_base_lines:
            return []

        new_base_lines = [
            self._prepare_base_line_for_taxes_computation(
                base_line,
                price_unit=base_line["price_unit"] * sign * percentage,
                computation_key=computation_key,
            )
            for base_line in reduced_base_lines
        ]
        self._add_tax_details_in_base_lines(new_base_lines, company)
        self._round_base_lines_tax_details(new_base_lines, company)

        sorted_base_lines = sorted(
            new_base_lines,
            key=lambda base_line: (
                bool(base_line["special_type"]),
                -base_line["tax_details"]["total_excluded_currency"],
            ),
        )
        current_tax_amounts_per_tax = self._measure_tax_amounts_per_tax(new_base_lines)
        for tax_id_str, tax_amounts in current_tax_amounts_per_tax.items():
            expected = expected_tax_amounts[tax_id_str]
            for delta_suffix, delta_currency in (
                ("_currency", currency),
                ("", company.currency_id),
            ):
                for prefix in ("tax", "base"):
                    reference_amount = tax_amounts[f"{prefix}_amount_currency"]
                    if not reference_amount:
                        continue

                    field = f"{prefix}_amount{delta_suffix}"
                    target_factors = [
                        {
                            "factor": abs(
                                tax_data[f"{prefix}_amount_currency"] / reference_amount
                            ),
                            "base_line": base_line,
                            "tax_data": tax_data,
                        }
                        for base_line in sorted_base_lines
                        for tax_data in base_line["tax_details"]["taxes_data"]
                        if str(tax_data["tax"].id) == tax_id_str
                    ]
                    amounts_to_distribute = self._distribute_delta_amount_smoothly(
                        precision_digits=delta_currency.decimal_places,
                        delta_amount=expected[field] - tax_amounts[field],
                        target_factors=target_factors,
                    )
                    for target_factor, amount_to_distribute in zip(
                        target_factors, amounts_to_distribute, strict=True
                    ):
                        target_factor["tax_data"][field] += amount_to_distribute

        self._spread_delta_on_base_amount(
            new_base_lines,
            sorted_base_lines,
            company,
            currency,
            expected_base_amount_currency,
            expected_base_amount,
        )

        return new_base_lines

    @api.model
    def _measure_base_lines_total(self, base_lines):
        values_per_grouping_key = self._aggregate_base_lines_aggregated_values(
            self._aggregate_base_lines_tax_details(
                base_lines, _group_everything_together
            )
        )
        return (
            sum(
                values["total_excluded_currency"] + values["tax_amount_currency"]
                for values in values_per_grouping_key.values()
            ),
            sum(
                values["total_excluded"] + values["tax_amount"]
                for values in values_per_grouping_key.values()
            ),
        )

    @api.model
    def _measure_tax_amounts_per_tax(self, base_lines):
        values_per_grouping_key = self._aggregate_base_lines_aggregated_values(
            self._aggregate_base_lines_tax_details(base_lines, _group_by_tax)
        )
        return {
            grouping_key: {
                "tax_amount_currency": values["tax_amount_currency"],
                "tax_amount": values["tax_amount"],
                "base_amount_currency": values["base_amount_currency"],
                "base_amount": values["base_amount"],
            }
            for grouping_key, values in values_per_grouping_key.items()
            if grouping_key
        }

    @api.model
    def _spread_delta_on_base_amount(
        self,
        new_base_lines,
        sorted_base_lines,
        company,
        currency,
        expected_base_amount_currency,
        expected_base_amount,
    ):
        """Nudge ``new_base_lines``' ``price_unit``s so their combined base
        amount matches ``expected_base_amount_currency``/``expected_base_amount``
        exactly, distributing the residual across ``sorted_base_lines`` via
        ``_distribute_delta_amount_smoothly``. Called by
        ``_reduce_base_lines_to_target_amount`` as its last step, after a plain
        proportional rescale has already gotten close but not exact due to
        per-line rounding.
        """
        current_base_amount_currency, current_base_amount = 0.0, 0.0
        values_per_grouping_key = self._aggregate_base_lines_aggregated_values(
            self._aggregate_base_lines_tax_details(
                new_base_lines, _group_everything_together
            )
        )
        for values in values_per_grouping_key.values():
            current_base_amount_currency += values["total_excluded_currency"]
            current_base_amount += values["total_excluded"]

        for delta_suffix, delta_base_amount, delta_currency in (
            (
                "_currency",
                expected_base_amount_currency - current_base_amount_currency,
                currency,
            ),
            ("", expected_base_amount - current_base_amount, company.currency_id),
        ):
            target_factors = [
                {
                    "factor": abs(
                        (
                            base_line["tax_details"]["total_excluded_currency"]
                            + base_line["tax_details"]["delta_total_excluded_currency"]
                        )
                        / current_base_amount_currency
                    )
                    if current_base_amount_currency
                    else 0.0,
                    "base_line": base_line,
                }
                for base_line in sorted_base_lines
            ]
            amounts_to_distribute = self._distribute_delta_amount_smoothly(
                precision_digits=delta_currency.decimal_places,
                delta_amount=delta_base_amount,
                target_factors=target_factors,
            )
            for target_factor, amount_to_distribute in zip(
                target_factors, amounts_to_distribute, strict=True
            ):
                base_line = target_factor["base_line"]
                base_line["tax_details"][f"delta_total_excluded{delta_suffix}"] += (
                    amount_to_distribute
                )
                if delta_suffix == "_currency":
                    base_line["price_unit"] += amount_to_distribute

    @api.model
    def _fix_base_lines_tax_details_on_manual_tax_amounts(
        self, base_lines, company, filter_function=None
    ):
        for base_line in base_lines:
            tax_details = base_line["tax_details"]
            taxes_data = tax_details["taxes_data"]
            if not taxes_data:
                continue

            base_line["manual_total_excluded_currency"] = (
                tax_details["total_excluded_currency"]
                + tax_details["delta_total_excluded_currency"]
            )
            base_line["manual_total_excluded"] = (
                tax_details["total_excluded"] + tax_details["delta_total_excluded"]
            )
            base_line["manual_tax_amounts"] = {}
            for tax_data in taxes_data:
                if tax_data["is_reverse_charge"]:
                    continue
                tax = tax_data["tax"]
                tax_id_str = str(tax.id)
                base_line["manual_tax_amounts"][tax_id_str] = {}
                if filter_function and not filter_function(base_line, tax_data):
                    continue

                base_line["manual_tax_amounts"][tax_id_str] = {
                    "tax_amount_currency": tax_data["tax_amount_currency"],
                    "tax_amount": tax_data["tax_amount"],
                    "base_amount_currency": tax_data["base_amount_currency"],
                    "base_amount": tax_data["base_amount"],
                }

    @api.model
    def _prepare_discountable_base_lines(
        self, base_lines, company, exclude_function=None
    ):
        return self._dispatch_taxes_into_new_base_lines(
            base_lines, company, self._get_undiscountable_filter(exclude_function)
        )

    @api.model
    def _prepare_global_discount_lines(
        self,
        base_lines,
        company,
        amount_type,
        amount,
        computation_key="global_discount",
        grouping_function=None,
    ):
        discountable_base_lines = self._prepare_discountable_base_lines(
            base_lines, company
        )
        new_base_lines = self._reduce_base_lines_to_target_amount(
            base_lines=discountable_base_lines,
            company=company,
            amount_type=amount_type,
            amount=-amount,
            computation_key=computation_key,
            grouping_function=grouping_function,
        )
        self._fix_base_lines_tax_details_on_manual_tax_amounts(
            base_lines=new_base_lines,
            company=company,
        )
        return new_base_lines

    @api.model
    def _finalize_dispatch(self, new_base_lines, dispatched_base_lines):
        """Drop the base lines that were fully consumed by a dispatch.

        Shared by ``_dispatch_global_discount_lines`` and
        ``_dispatch_return_of_merchandise_lines``: both dispatch a subset of
        their input lines (discount lines, return lines) into new lines
        attached to other base lines, and must exclude the now-redundant
        originals from their own return value. Identity-based (``id()``) since
        base line dicts are not hashable and are never deduplicated by value.
        """
        dispatched_ids = {id(x) for x in dispatched_base_lines}
        return [x for x in new_base_lines if id(x) not in dispatched_ids]

    @api.model
    def _dispatch_global_discount_lines(self, base_lines, company):
        """Split each ``special_type == "global_discount"`` line, proportionally
        by ``raw_total_excluded_currency``, across the other base_lines that
        share its discountable tax set, appending the resulting parts to each
        target line's ``discount_base_lines`` list. Companion to
        ``_squash_global_discount_lines``, which merges those parts back in.
        Returns ``base_lines`` with the now-redundant discount lines removed
        (see ``_finalize_dispatch``); lines with no discountable counterpart
        are left untouched (their discount line, if any, has no target and is
        not dispatched).
        """
        new_base_lines = []
        discount_data_per_taxes = {}
        dispatched_neg_base_lines = []
        for base_line in base_lines:
            tax_details = base_line["tax_details"]
            taxes_data = tax_details["taxes_data"]

            taxes = self.env["account.tax"]
            for gb_tax_data in taxes_data:
                taxes += gb_tax_data["tax"]
            taxes = taxes.filtered(lambda tax: tax._can_be_discounted())

            discount_data = discount_data_per_taxes.setdefault(
                taxes,
                {
                    "base_lines": [],
                    "discount_base_lines": [],
                },
            )

            new_base_line = {
                **base_line,
                "discount_base_lines": [],
            }

            if base_line["special_type"] == "global_discount":
                discount_data["discount_base_lines"].append(new_base_line)
            else:
                discount_data["base_lines"].append(new_base_line)
            new_base_lines.append(new_base_line)

        for discount_data in discount_data_per_taxes.values():
            discount_data["target_factors"] = [
                {
                    "base_line": base_line,
                    "factor": base_line["tax_details"]["raw_total_excluded_currency"],
                }
                for base_line in discount_data["base_lines"]
            ]
            if discount_data["target_factors"]:
                dispatched_neg_base_lines += discount_data["discount_base_lines"]
            else:
                continue

            for discount_base_line in discount_data["discount_base_lines"]:
                splitted_base_lines = self._split_base_line(
                    base_line=discount_base_line,
                    company=company,
                    target_factors=discount_data["target_factors"],
                )
                for base_line, new_base_line in zip(
                    discount_data["base_lines"], splitted_base_lines, strict=True
                ):
                    base_line["discount_base_lines"].append(new_base_line)
        return self._finalize_dispatch(new_base_lines, dispatched_neg_base_lines)

    @api.model
    def _squash_global_discount_lines(self, base_lines, company):
        """Merge each base_line's ``discount_base_lines`` (populated by
        ``_dispatch_global_discount_lines``) back into its own ``tax_details``
        in place, then re-fix any manual tax amount overrides on the lines
        that actually received a discount split.
        """
        for base_line in base_lines:
            for sub_base_line in base_line["discount_base_lines"]:
                base_line["tax_details"] = self._merge_tax_details(
                    tax_details_1=base_line["tax_details"],
                    tax_details_2=sub_base_line["tax_details"],
                )

        self._fix_base_lines_tax_details_on_manual_tax_amounts(
            base_lines=[
                base_line
                for base_line in base_lines
                if base_line["discount_base_lines"]
            ],
            company=company,
        )

    @api.model
    def _prepare_base_lines_for_down_payment(
        self,
        base_lines,
        company,
        exclude_function=None,
    ):
        new_base_lines = self._dispatch_taxes_into_new_base_lines(
            base_lines,
            company,
            self._get_undiscountable_filter(exclude_function),
        )
        return new_base_lines + self._turn_removed_taxes_into_new_base_lines(
            new_base_lines,
            company,
        )

    @api.model
    def _prepare_down_payment_lines(
        self,
        base_lines,
        company,
        amount_type,
        amount,
        computation_key="down_payment",
        grouping_function=None,
    ):
        base_lines_for_dp = self._prepare_base_lines_for_down_payment(
            base_lines, company
        )
        new_base_lines = self._reduce_base_lines_to_target_amount(
            base_lines=base_lines_for_dp,
            company=company,
            amount_type=amount_type,
            amount=amount,
            computation_key=computation_key,
            grouping_function=grouping_function,
        )
        self._fix_base_lines_tax_details_on_manual_tax_amounts(
            base_lines=new_base_lines,
            company=company,
        )
        return new_base_lines

    @api.model
    def _dispatch_return_of_merchandise_lines(self, base_lines, company):
        """Match negative-quantity (return) lines against positive-quantity
        lines of the same product/grouping (``_group_lines_for_return_of_merchandise``,
        ``_match_returns_to_positive_lines``: a greedy, quantity-sorted match),
        splitting each return line proportionally across the positive lines it
        was matched to and appending the resulting parts to each positive
        line's ``return_of_merchandise_base_lines``. A return quantity that
        exceeds all available positive quantity is *not* silently dropped: the
        matcher assigns the unmatched remainder a target factor with
        ``plus_base_line: None``, which this method turns into a new,
        standalone base line (no positive counterpart to attach to) instead of
        appending it anywhere. Companion to ``_squash_return_of_merchandise_lines``.
        Returns ``base_lines`` with the now-redundant return lines removed
        (see ``_finalize_dispatch``).
        """
        dispatched_neg_base_lines = []
        new_base_lines, mapping = self._group_lines_for_return_of_merchandise(
            base_lines
        )

        for signed_base_lines in mapping.values():
            neg_base_lines = sorted(
                signed_base_lines["-"], key=lambda base_line: base_line["quantity"]
            )
            target_factors_per_neg_base_line = self._match_returns_to_positive_lines(
                sorted(
                    signed_base_lines["+"],
                    key=lambda base_line: -base_line["quantity"],
                ),
                neg_base_lines,
            )

            def update_kwargs(base_line, target_factor, kwargs):
                kwargs["price_unit"] = base_line["price_unit"]
                kwargs["quantity"] = -target_factor["quantity_to_dispatch"]

            for target_factors, neg_base_line in zip(
                target_factors_per_neg_base_line, neg_base_lines, strict=True
            ):
                if not target_factors:
                    continue

                dispatched_neg_base_lines.append(neg_base_line)
                splitted_base_lines = self._split_base_line(
                    base_line=neg_base_line,
                    company=company,
                    target_factors=target_factors,
                    update_kwargs=update_kwargs,
                )
                for target_factor, new_base_line in zip(
                    target_factors, splitted_base_lines, strict=True
                ):
                    plus_base_line = target_factor["plus_base_line"]
                    if plus_base_line:
                        plus_base_line["return_of_merchandise_base_lines"].append(
                            new_base_line
                        )
                    else:
                        new_base_line["return_of_merchandise_base_lines"] = []
                        new_base_lines.append(new_base_line)

        return self._finalize_dispatch(new_base_lines, dispatched_neg_base_lines)

    @api.model
    def _group_lines_for_return_of_merchandise(self, base_lines):
        new_base_lines = []
        mapping = defaultdict(lambda: {"+": [], "-": []})
        for base_line in base_lines:
            new_base_line = {**base_line, "return_of_merchandise_base_lines": []}
            new_base_lines.append(new_base_line)

            if not base_line["product_id"] or base_line["quantity"] == 0:
                continue

            key = frozendict(
                {
                    "tax_ids": base_line["tax_ids"].ids,
                    "product": base_line["product_id"].id,
                    "price_unit": base_line["price_unit"],
                    "discount": base_line["discount"],
                }
            )
            is_negative = base_line["tax_details"]["raw_total_excluded_currency"] < 0.0
            mapping[key]["-" if is_negative else "+"].append(new_base_line)
        return new_base_lines, mapping

    @api.model
    def _match_returns_to_positive_lines(self, plus_base_lines, neg_base_lines):
        target_factors_per_neg_base_line = [[] for _neg in neg_base_lines]

        iter_plus_base_lines = iter(plus_base_lines)
        plus_base_line = next(iter_plus_base_lines, None)
        plus_quantity = abs(plus_base_line["quantity"]) if plus_base_line else 0.0

        for target_factors, neg_base_line in zip(
            target_factors_per_neg_base_line, neg_base_lines, strict=True
        ):
            neg_quantity = abs(neg_base_line["quantity"])
            remaining = neg_quantity
            while not float_is_zero(remaining, precision_digits=12) and (
                plus_base_line
            ):
                if float_is_zero(plus_quantity, precision_digits=12):
                    plus_base_line = next(iter_plus_base_lines, None)
                    plus_quantity = (
                        abs(plus_base_line["quantity"]) if plus_base_line else 0.0
                    )
                    continue

                quantity_to_dispatch = min(remaining, plus_quantity)
                target_factors.append(
                    {
                        "factor": quantity_to_dispatch / neg_quantity,
                        "quantity_to_dispatch": quantity_to_dispatch,
                        "plus_base_line": plus_base_line,
                    }
                )
                plus_quantity -= quantity_to_dispatch
                remaining -= quantity_to_dispatch

            if target_factors and not float_is_zero(remaining, precision_digits=12):
                target_factors.append(
                    {
                        "factor": remaining / neg_quantity,
                        "quantity_to_dispatch": remaining,
                        "plus_base_line": None,
                    }
                )
        return target_factors_per_neg_base_line

    @api.model
    def _squash_return_of_merchandise_lines(self, base_lines, company):
        """Merge each base_line's ``return_of_merchandise_base_lines``
        (populated by ``_dispatch_return_of_merchandise_lines``) back into its
        own ``tax_details`` and ``quantity`` in place, then re-fix any manual
        tax amount overrides on the lines that actually absorbed a return.
        """
        for base_line in base_lines:
            for sub_base_line in base_line["return_of_merchandise_base_lines"]:
                base_line["tax_details"] = self._merge_tax_details(
                    tax_details_1=base_line["tax_details"],
                    tax_details_2=sub_base_line["tax_details"],
                )
                base_line["quantity"] += sub_base_line["quantity"]

        self._fix_base_lines_tax_details_on_manual_tax_amounts(
            base_lines=[
                base_line
                for base_line in base_lines
                if base_line["return_of_merchandise_base_lines"]
            ],
            company=company,
        )

    @api.model
    def _get_delta_amount_to_reach_target(
        self,
        target_amount,
        target_currency,
        raw_current_amount,
        raw_current_amount_precision_digits,
    ):
        """Return the delta to add to ``raw_current_amount`` to bring it back
        within tolerance of ``target_amount``, or 0.0 if it already is.

        The tolerance window is ``abs(target_amount) +/- target_currency.rounding / 2``.
        ``raw_current_amount_rounding`` (one unit of precision at
        ``raw_current_amount_precision_digits``) is subtracted only from the
        upper bound, not added back to the lower one: the upper bound is
        computed by *adding* half the currency rounding, so shrinking it by one
        precision unit compensates for `float_round`'s own rounding pushing a
        borderline value up past the boundary and being wrongly seen as
        in-tolerance. The lower bound is computed by *subtracting* half the
        currency rounding already, so it does not need — and must not get —
        the same nudge in the same direction, or it would loosen instead of
        tighten the tolerance.
        """
        target_amount_sign = -1 if target_amount < 0.0 else 1
        raw_current_amount_rounding = math.pow(10, -raw_current_amount_precision_digits)
        tolerance_bounds = (
            float_round(
                abs(target_amount)
                + (target_currency.rounding / 2)
                - raw_current_amount_rounding,
                precision_digits=raw_current_amount_precision_digits,
            ),
            float_round(
                abs(target_amount) - (target_currency.rounding / 2),
                precision_digits=raw_current_amount_precision_digits,
            ),
        )

        signed_raw_current_amount = target_amount_sign * raw_current_amount
        if signed_raw_current_amount > tolerance_bounds[0]:
            delta_raw_amount = tolerance_bounds[0] - signed_raw_current_amount
        elif signed_raw_current_amount < tolerance_bounds[1]:
            delta_raw_amount = tolerance_bounds[1] - signed_raw_current_amount
        else:
            return 0.0

        return target_amount_sign * delta_raw_amount

    @api.model
    def _round_raw_total_excluded(
        self,
        base_lines,
        company,
        precision_digits=6,
        apply_strict_tolerance=False,
        in_foreign_currency=True,
    ):
        """Round each base_line's ``raw_total_excluded[_currency]`` to
        ``precision_digits`` in place. With ``apply_strict_tolerance``, also
        reconciles the sum of the now-rounded per-line values against the
        group's own expected total (via ``_get_delta_amount_to_reach_target`` +
        ``_distribute_delta_amount_smoothly``), so many small per-line roundings
        can't drift the aggregate total outside its tolerance window. Part of
        the ``raw_``/``target_``/``delta_`` rounding-reconciliation family also
        used by ``_apply_gross_total_strict_tolerance``,
        ``_round_raw_gross_total_excluded_and_discount``, and
        ``_apply_raw_tax_amounts_tolerance``.
        """
        if not base_lines:
            return

        suffix_currency = (
            base_lines[0]["currency_id"] if in_foreign_currency else company.currency_id
        )
        suffix = "_currency" if in_foreign_currency else ""
        raw_field = f"raw_total_excluded{suffix}"

        for base_line in base_lines:
            tax_details = base_line["tax_details"]
            tax_details[raw_field] = float_round(
                tax_details[raw_field], precision_digits=precision_digits
            )

        if not apply_strict_tolerance:
            return

        base_lines_aggregated_values = self._aggregate_base_lines_tax_details(
            base_lines, _group_everything_together
        )
        values_per_grouping_key = self._aggregate_base_lines_aggregated_values(
            base_lines_aggregated_values
        )
        expected_total_excluded = sum(
            values[f"total_excluded{suffix}"]
            for values in values_per_grouping_key.values()
        )
        current_raw_total_excluded = sum(
            base_line["tax_details"][raw_field] for base_line in base_lines
        )

        delta_raw_amount = self._get_delta_amount_to_reach_target(
            target_amount=expected_total_excluded,
            target_currency=suffix_currency,
            raw_current_amount=current_raw_total_excluded,
            raw_current_amount_precision_digits=precision_digits,
        )
        target_factors = [
            {
                "factor": base_line["tax_details"][raw_field],
                "base_line": base_line,
            }
            for base_line in base_lines
        ]
        amounts_to_distribute = self._distribute_delta_amount_smoothly(
            precision_digits=precision_digits,
            delta_amount=delta_raw_amount,
            target_factors=target_factors,
        )
        for target_factor, amount_to_distribute in zip(
            target_factors, amounts_to_distribute, strict=True
        ):
            base_line = target_factor["base_line"]
            base_line["tax_details"][raw_field] += amount_to_distribute

    @api.model
    def _get_price_unit_without_tax(
        self,
        base_line,
        raw_gross_total_excluded,
        in_foreign_currency=True,
        precision_digits=None,
    ):
        if not raw_gross_total_excluded or (
            precision_digits is not None
            and float_is_zero(
                raw_gross_total_excluded, precision_digits=precision_digits
            )
        ):
            if in_foreign_currency:
                raw_gross_price_unit = base_line["price_unit"]
            elif base_line["rate"]:
                raw_gross_price_unit = base_line["price_unit"] / base_line["rate"]
            else:
                raw_gross_price_unit = 0.0
        elif not base_line["quantity"]:
            raw_gross_price_unit = raw_gross_total_excluded
        else:
            raw_gross_price_unit = raw_gross_total_excluded / base_line["quantity"]

        if precision_digits is not None:
            raw_gross_price_unit = float_round(
                raw_gross_price_unit, precision_digits=precision_digits
            )
        return raw_gross_price_unit

    @api.model
    def _get_discount_amount_without_tax(
        self,
        base_line,
        raw_gross_total_excluded,
        in_foreign_currency=True,
        precision_digits=None,
    ):
        suffix = "_currency" if in_foreign_currency else ""
        raw_discount_amount = (
            raw_gross_total_excluded
            - base_line["tax_details"][f"raw_total_excluded{suffix}"]
        )

        if precision_digits is not None:
            raw_discount_amount = float_round(
                raw_discount_amount, precision_digits=precision_digits
            )
        return raw_discount_amount

    @api.model
    def _add_and_round_raw_gross_total_excluded_and_discount(
        self,
        base_lines,
        company,
        precision_digits=6,
        apply_strict_tolerance=False,
        in_foreign_currency=True,
        account_discount_base_lines=False,
    ):
        if not base_lines:
            return

        suffix_currency = (
            base_lines[0]["currency_id"] if in_foreign_currency else company.currency_id
        )
        suffix = "_currency" if in_foreign_currency else ""
        raw_field = f"raw_total_excluded{suffix}"

        for base_line in base_lines:
            tax_details = base_line["tax_details"]
            raw_total_excluded = tax_details[raw_field]

            global_discount_sum = 0.0
            if account_discount_base_lines:
                global_discount_sum = sum(
                    discount_base_line["tax_details"][raw_field]
                    for discount_base_line in base_line.get("discount_base_lines", [])
                )

            discount_factor = 1 - (base_line["discount"] / 100.0)
            if discount_factor:
                raw_gross_total_excluded = (
                    raw_total_excluded - global_discount_sum
                ) / discount_factor
            elif suffix == "_currency":
                raw_gross_total_excluded = (
                    base_line["price_unit"] * base_line["quantity"]
                )
            elif base_line["rate"]:
                raw_gross_total_excluded = (
                    base_line["price_unit"] * base_line["quantity"] / base_line["rate"]
                )
            else:
                raw_gross_total_excluded = 0.0
            tax_details[f"raw_gross_total_excluded{suffix}"] = float_round(
                raw_gross_total_excluded, precision_digits=precision_digits
            )

            raw_gross_price_unit = self._get_price_unit_without_tax(
                base_line=base_line,
                raw_gross_total_excluded=raw_gross_total_excluded,
                in_foreign_currency=in_foreign_currency,
                precision_digits=precision_digits,
            )
            tax_details[f"raw_gross_price_unit{suffix}"] = raw_gross_price_unit

            raw_discount_amount = self._get_discount_amount_without_tax(
                base_line=base_line,
                raw_gross_total_excluded=raw_gross_total_excluded,
                in_foreign_currency=in_foreign_currency,
                precision_digits=precision_digits,
            )
            tax_details[f"raw_discount_amount{suffix}"] = raw_discount_amount

        if apply_strict_tolerance:
            self._apply_gross_total_strict_tolerance(
                base_lines, suffix, suffix_currency, precision_digits
            )

    @api.model
    def _apply_gross_total_strict_tolerance(
        self, base_lines, suffix, suffix_currency, precision_digits
    ):
        """Reconcile the sum of ``base_lines``' already-rounded
        ``raw_total_excluded[_currency]`` against the group's expected total
        (aggregated tax-detail values), redistributing any residual across the
        lines via ``_distribute_delta_amount_smoothly``. Called by
        ``_round_raw_total_excluded`` when ``apply_strict_tolerance=True``; see
        that method's docstring for the family this belongs to.
        """
        base_lines_aggregated_values = self._aggregate_base_lines_tax_details(
            base_lines, _group_everything_together
        )
        values_per_grouping_key = self._aggregate_base_lines_aggregated_values(
            base_lines_aggregated_values
        )
        grouped_base_lines = [
            base_line
            for values in values_per_grouping_key.values()
            for base_line, _taxes_data in values["base_line_x_taxes_data"]
        ]
        expected_total_excluded = sum(
            values[f"total_excluded{suffix}"]
            for values in values_per_grouping_key.values()
        )
        raw_total_discount_amount = sum(
            base_line["tax_details"][f"raw_discount_amount{suffix}"]
            for base_line in grouped_base_lines
        )
        raw_total_gross_amount = sum(
            base_line["tax_details"][f"raw_gross_total_excluded{suffix}"]
            for base_line in grouped_base_lines
        )
        expected_total_gross_amount = expected_total_excluded + suffix_currency.round(
            raw_total_discount_amount
        )

        delta_raw_amount = self._get_delta_amount_to_reach_target(
            target_amount=expected_total_gross_amount,
            target_currency=suffix_currency,
            raw_current_amount=raw_total_gross_amount,
            raw_current_amount_precision_digits=precision_digits,
        )
        target_factors = [
            {
                "factor": base_line["tax_details"][f"raw_total_excluded{suffix}"],
                "base_line": base_line,
            }
            for base_line in grouped_base_lines
        ]
        amounts_to_distribute = self._distribute_delta_amount_smoothly(
            precision_digits=precision_digits,
            delta_amount=delta_raw_amount,
            target_factors=target_factors,
        )
        for target_factor, amount_to_distribute in zip(
            target_factors, amounts_to_distribute, strict=True
        ):
            base_line = target_factor["base_line"]
            base_line["tax_details"][f"raw_gross_total_excluded{suffix}"] += (
                amount_to_distribute
            )

    @api.model
    def _round_raw_gross_total_excluded_and_discount(
        self,
        base_lines,
        company,
        in_foreign_currency=True,
    ):
        """Round each base_line's ``raw_gross_total_excluded[_currency]`` (the
        pre-discount total, computed via ``_get_price_unit_without_tax``/
        ``_get_discount_amount_without_tax``) and its discount amount, then
        reconcile the rounded sum back to the group's expected gross total.
        Same rounding-reconciliation shape as ``_round_raw_total_excluded``,
        applied to the gross (pre-discount) field instead.
        """
        if not base_lines:
            return

        suffix_currency = (
            base_lines[0]["currency_id"] if in_foreign_currency else company.currency_id
        )
        suffix = "_currency" if in_foreign_currency else ""

        current_gross_total_excluded = 0.0
        current_discount_amount = 0.0
        current_raw_discount_amount = 0.0
        for base_line in base_lines:
            tax_details = base_line["tax_details"]
            gross_total_excluded = tax_details[f"gross_total_excluded{suffix}"] = (
                float_round(
                    value=tax_details[f"raw_gross_total_excluded{suffix}"],
                    precision_rounding=suffix_currency.rounding,
                )
            )
            current_gross_total_excluded += gross_total_excluded

            raw_discount_amount = tax_details[f"raw_discount_amount{suffix}"]
            discount_amount = tax_details[f"discount_amount{suffix}"] = float_round(
                value=raw_discount_amount,
                precision_rounding=suffix_currency.rounding,
            )
            current_discount_amount += discount_amount
            current_raw_discount_amount += raw_discount_amount

        base_lines_aggregated_values = self._aggregate_base_lines_tax_details(
            base_lines, _group_everything_together
        )
        values_per_grouping_key = self._aggregate_base_lines_aggregated_values(
            base_lines_aggregated_values
        )
        expected_total_excluded = sum(
            values[f"total_excluded{suffix}"]
            for values in values_per_grouping_key.values()
        )

        expected_gross_total_excluded = expected_total_excluded + float_round(
            value=current_raw_discount_amount,
            precision_rounding=suffix_currency.rounding,
        )

        target_factors = [
            {
                "factor": 1.0,
                "base_line": base_line,
            }
            for base_line in base_lines
        ]
        expected_discount_amount = (
            expected_gross_total_excluded - expected_total_excluded
        )
        for field, delta_amount in (
            (
                f"gross_total_excluded{suffix}",
                expected_gross_total_excluded - current_gross_total_excluded,
            ),
            (
                f"discount_amount{suffix}",
                expected_discount_amount - current_discount_amount,
            ),
        ):
            amounts_to_distribute = self._distribute_delta_amount_smoothly(
                precision_digits=suffix_currency.decimal_places,
                delta_amount=delta_amount,
                target_factors=target_factors,
            )
            for target_factor, amount_to_distribute in zip(
                target_factors, amounts_to_distribute, strict=True
            ):
                target_factor["base_line"]["tax_details"][field] += amount_to_distribute

    @api.model
    def _round_raw_tax_amounts(
        self,
        base_lines_aggregated_values,
        company,
        precision_digits=6,
        apply_strict_tolerance=False,
        in_foreign_currency=True,
    ):
        if not base_lines_aggregated_values:
            return

        suffix_currency = (
            base_lines_aggregated_values[0][0]["currency_id"]
            if in_foreign_currency
            else company.currency_id
        )
        suffix = "_currency" if in_foreign_currency else ""

        for _base_line, aggregated_values in base_lines_aggregated_values:
            for values in aggregated_values.values():
                values[f"raw_tax_amount{suffix}"] = float_round(
                    values[f"raw_tax_amount{suffix}"], precision_digits=precision_digits
                )
                values[f"raw_base_amount{suffix}"] = float_round(
                    values[f"raw_base_amount{suffix}"],
                    precision_digits=precision_digits,
                )

        if apply_strict_tolerance:
            self._apply_raw_tax_amounts_tolerance(
                base_lines_aggregated_values, suffix, suffix_currency, precision_digits
            )

    @api.model
    def _apply_raw_tax_amounts_tolerance(
        self, base_lines_aggregated_values, suffix, suffix_currency, precision_digits
    ):
        """Reconcile each per-tax group's rounded ``raw_tax_amount[_currency]``
        against its own expected tax amount, then derive and reconcile the
        matching ``raw_base_amount[_currency]`` from the (constant, per-group)
        tax rate. Called by ``_round_raw_tax_amounts`` when
        ``apply_strict_tolerance=True``; same rounding-reconciliation family as
        ``_round_raw_total_excluded``. Note: the per-line weights used to
        distribute the residual are snapshotted once per group and reused for
        both the tax-amount and the base-amount redistribution passes below;
        this only affects which line(s) absorb a sub-cent residual; the
        redistributed total is always exact regardless.
        """
        tax_field = f"tax_amount{suffix}"
        raw_tax_field = f"raw_{tax_field}"
        base_field = f"base_amount{suffix}"
        raw_base_field = f"raw_{base_field}"
        values_per_grouping_key = self._aggregate_base_lines_aggregated_values(
            base_lines_aggregated_values
        )
        for grouping_key, values in values_per_grouping_key.items():
            tax_rate = (
                (values[raw_tax_field] / values[raw_base_field])
                if values[raw_base_field]
                else 0.0
            )

            target_factors = [
                {
                    "factor": aggregated_values[grouping_key][raw_tax_field],
                    "aggregated_values": aggregated_values[grouping_key],
                }
                for base_line, aggregated_values in base_lines_aggregated_values
                if grouping_key in aggregated_values
            ]

            expected_tax_amount = values[tax_field]
            current_raw_tax_amount = values[raw_tax_field]
            delta_raw_amount = self._get_delta_amount_to_reach_target(
                target_amount=expected_tax_amount,
                target_currency=suffix_currency,
                raw_current_amount=current_raw_tax_amount,
                raw_current_amount_precision_digits=precision_digits,
            )
            amounts_to_distribute = self._distribute_delta_amount_smoothly(
                precision_digits=precision_digits,
                delta_amount=delta_raw_amount,
                target_factors=target_factors,
            )
            for target_factor, amount_to_distribute in zip(
                target_factors, amounts_to_distribute, strict=True
            ):
                aggregated_values = target_factor["aggregated_values"]
                aggregated_values[raw_tax_field] += amount_to_distribute
                values[raw_tax_field] += amount_to_distribute
                if amount_to_distribute and tax_rate:
                    new_raw_base_amount = aggregated_values[raw_tax_field] / tax_rate
                    rounded_new_raw_base_amount = float_round(
                        new_raw_base_amount, precision_digits=precision_digits
                    )
                    values[raw_base_field] += (
                        rounded_new_raw_base_amount - aggregated_values[raw_base_field]
                    )
                    aggregated_values[raw_base_field] = rounded_new_raw_base_amount

            if tax_rate:
                current_tax_raw_base_amount = (
                    current_raw_tax_amount + delta_raw_amount
                ) / tax_rate
                delta_raw_amount = self._get_delta_amount_to_reach_target(
                    target_amount=current_tax_raw_base_amount,
                    target_currency=suffix_currency,
                    raw_current_amount=values[raw_base_field],
                    raw_current_amount_precision_digits=precision_digits,
                )
                amounts_to_distribute = self._distribute_delta_amount_smoothly(
                    precision_digits=precision_digits,
                    delta_amount=delta_raw_amount,
                    target_factors=target_factors,
                )
                for target_factor, amount_to_distribute in zip(
                    target_factors, amounts_to_distribute, strict=True
                ):
                    aggregated_values = target_factor["aggregated_values"]
                    aggregated_values[raw_base_field] += amount_to_distribute
                    values[raw_base_field] += amount_to_distribute

    def _get_all_special_mode(self, handle_price_include):
        if "force_price_include" in self.env.context:
            return (
                "total_included"
                if self.env.context["force_price_include"]
                else "total_excluded"
            )
        if not handle_price_include:
            return "total_excluded"
        return False

    def flatten_taxes_hierarchy(self):
        return self._flatten_taxes_and_sort_them()[0]

    def compute_all(
        self,
        price_unit,
        currency=None,
        quantity=1.0,
        product=None,
        partner=None,
        is_refund=False,
        handle_price_include=True,
        rounding_method=None,
    ):
        """Legacy-shaped, single-line entry point to the tax engine: takes one
        ``price_unit``/``quantity`` pair and returns the older
        ``{"taxes": [...], "total_excluded", "total_included", ...}``
        dict shape. Internally it just builds one base line via
        ``_prepare_base_line_for_taxes_computation`` and delegates to
        ``_add_tax_details_in_base_line`` — the same batch pipeline used
        elsewhere in this file — then reshapes the result back to this
        contract. Kept for callers needing the single-line/legacy shape (there
        are many across the addons tree); new code computing taxes for more
        than one line at a time should use the base-lines batch API
        (``_prepare_base_line_for_taxes_computation`` /
        ``_add_tax_details_in_base_lines``) directly instead, since this method
        pays the per-line dict-building overhead once per call.
        """
        company = self._get_settings_company()
        company = company._get_accessible_branches()[:1] or company

        currency = currency or company.currency_id
        special_mode = self._get_all_special_mode(handle_price_include)

        base_line = self._prepare_base_line_for_taxes_computation(
            None,
            partner_id=partner,
            currency_id=currency,
            product_id=product,
            tax_ids=self,
            price_unit=price_unit,
            quantity=quantity,
            is_refund=is_refund,
            special_mode=special_mode,
        )
        self._add_tax_details_in_base_line(
            base_line, company, rounding_method=rounding_method
        )

        tax_details = base_line["tax_details"]
        total_excluded = tax_details["raw_total_excluded_currency"]
        total_included = tax_details["raw_total_included_currency"]

        taxes = []
        for tax_data in tax_details["taxes_data"]:
            tax = tax_data["tax"]
            taxes.append(
                {
                    "id": tax.id,
                    "name": (partner and tax.with_context(lang=partner.lang).name)
                    or tax.name,
                    "amount": tax_data["raw_tax_amount_currency"],
                    "base": tax_data["raw_base_amount_currency"],
                    "sequence": tax.sequence,
                    "price_include": tax.price_include,
                    "is_reverse_charge": tax_data["is_reverse_charge"],
                    "group": tax_data["group"],
                }
            )

        if self.env.context.get("round_base", True):
            total_excluded = currency.round(total_excluded)
            total_included = currency.round(total_included)

        return {
            "taxes": taxes,
            "total_excluded": total_excluded,
            "total_included": total_included,
        }

    def _filter_taxes_by_company(self, company_id):
        if not self:
            return self
        taxes, company = self.env["account.tax"], company_id
        while not taxes and company:
            taxes = self.sudo().filtered(lambda t, c=company: c in t.company_ids)
            company = company.sudo().parent_id
        return taxes.with_env(self.env)

    @api.model
    def _fix_tax_included_price(self, price, prod_taxes, line_taxes):
        prod_taxes = prod_taxes._origin
        line_taxes = line_taxes._origin
        incl_tax = prod_taxes.filtered(
            lambda tax: tax not in line_taxes and tax.price_include
        )
        if incl_tax:
            return incl_tax.compute_all(price)["total_excluded"]
        return price

    @api.model
    def _fix_tax_included_price_company(
        self, price, prod_taxes, line_taxes, company_id
    ):
        if company_id:
            prod_taxes = prod_taxes.filtered(
                lambda tax: tax._serves_company(company_id)
            )
            line_taxes = line_taxes.filtered(
                lambda tax: tax._serves_company(company_id)
            )
        return self._fix_tax_included_price(price, prod_taxes, line_taxes)

    def _get_description_plaintext(self):
        self.check_singleton()
        if is_html_empty(self.description):
            return ""
        return html2plaintext(self.description)


class AccountTaxRepartitionLine(models.Model):
    _name = "account.tax.repartition.line"
    _description = "Tax Repartition Line"
    _order = "document_type, repartition_type, sequence, id"
    _check_company_auto = True
    _check_company_domain = models.check_companies_domain_parent_of

    factor_percent = fields.Float(
        string="%",
        digits=(16, 12),
        default=100,
        required=True,
        help="Factor to apply on the account move lines generated from this distribution line, in percents",
    )
    factor = fields.Float(
        string="Factor Ratio",
        compute="_compute_factor",
        help="Factor to apply on the account move lines generated from this distribution line",
    )
    repartition_type = fields.Selection(
        selection=[("base", "Base"), ("tax", "of tax")],
        string="Based On",
        default="tax",
        required=True,
        help="Base on which the factor will be applied.",
    )
    document_type = fields.Selection(
        selection=[("invoice", "Invoice"), ("refund", "Refund")],
        string="Related to",
        required=True,
    )
    tax_id = fields.Many2one(
        comodel_name="account.tax",
        index="btree_not_null",
        ondelete="cascade",
        check_company=True,
    )
    company_ids = fields.Many2many(
        comodel_name="res.company",
        related="tax_id.company_ids",
        string="Companies",
        help="The companies this distribution line belongs to.",
    )
    sequence = fields.Integer(
        default=1,
        help="The order in which distribution lines are displayed and matched. "
        "For refunds to work properly, invoice distribution lines should be "
        "arranged in the same order as the credit note distribution lines "
        "they correspond to.",
    )

    @api.depends("factor_percent")
    def _compute_factor(self):
        for record in self:
            record.factor = record.factor_percent / 100.0
