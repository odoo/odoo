from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog
from odoo.tools import float_compare

CHATTER_PRODUCT_LIST_THRESHOLD = 50

_debug = DebugLog(__name__)


class MixinOrderLineFields(models.AbstractModel):
    _name = "mixin.order.line.fields"
    _description = "Common Order Line Fields"

    _order_type = ""
    _product_ok_field = ""
    _analytic_business_domain = ""
    _transfer_verb = "transferred"

    order_id = fields.Many2one(
        comodel_name="mixin.order",
        string="Order Reference",
        index=True,
        required=True,
        ondelete="cascade",
    )

    company_id = fields.Many2one(
        comodel_name="res.company",
        related="order_id.company_id",
        string="Company",
    )
    company_price_include = fields.Selection(related="company_id.account_price_include")
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="order_id.currency_id",
        string="Currency",
        depends=["order_id.currency_id"],
    )
    partner_id = fields.Many2one(  # noqa: E8529  One2many inverse of res.partner's order line lists
        comodel_name="res.partner",
        related="order_id.partner_id",
        string="Partner",
        precompute=True,
        store=True,
        index="btree_not_null",
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        related="order_id.user_id",
        string="Responsible",
    )
    date_order = fields.Datetime(
        related="order_id.date_order",
        string="Order Date",
    )
    date_confirmed = fields.Datetime(
        related="order_id.date_confirmed",
        string="Confirmation Date",
    )
    state = fields.Selection(
        related="order_id.state",
        string="Order Status",
    )
    fiscal_position_id = fields.Many2one(
        comodel_name="account.fiscal.position",
        related="order_id.fiscal_position_id",
    )
    tax_country_id = fields.Many2one(
        comodel_name="res.country",
        related="order_id.tax_country_id",
    )
    locked = fields.Boolean(related="order_id.locked")

    product_categ_id = fields.Many2one(related="product_id.categ_id")
    product_type = fields.Selection(
        related="product_id.type",
        depends=["product_id"],
    )

    # A model that re-declares `parent_id` to narrow `comodel_name` (see
    # e.g. `purchase.order.line`) keeps this `compute=` only because Odoo's
    # field-merge rules carry over a base field's kwargs when the redeclared
    # type still matches. Redeclaring with a *different* field type would
    # silently clear `compute` instead of raising -- keep any such override
    # a `fields.Many2one` too.
    parent_id = fields.Many2one(
        comodel_name="mixin.order.line.fields",
        string="Parent Section Line",
        compute="_compute_parent_id",
    )

    sequence = fields.Integer(default=10)

    display_type = fields.Selection(
        selection=[
            ("line_section", "Section"),
            ("line_subsection", "Subsection"),
            ("line_note", "Note"),
        ],
        default=False,
    )

    product_id = fields.Many2one(
        comodel_name="product.product",
        change_default=True,
        index="btree_not_null",
        domain=lambda self: self._domain_product_id(),
        ondelete="restrict",
        check_company=True,
    )

    product_template_attribute_value_ids = fields.Many2many(
        related="product_id.product_template_attribute_value_ids",
        depends=["product_id"],
    )
    product_name_translated = fields.Text(compute="_compute_product_name_translated")
    product_is_archived = fields.Boolean(compute="_compute_product_is_archived")
    allowed_uom_ids = fields.Many2many(
        comodel_name="uom.uom",
        compute="_compute_allowed_uom_ids",
    )
    product_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="Unit",
        compute="_compute_product_uom_id",
        precompute=True,
        store=True,
        readonly=False,
        domain='[("id", "in", allowed_uom_ids)]',
        ondelete="restrict",
    )

    name = fields.Text(
        string="Description",
        compute="_compute_name",
        precompute=True,
        store=True,
        readonly=False,
        required=True,
    )

    is_downpayment = fields.Boolean(string="Is a down payment")

    is_expense = fields.Boolean(
        string="Is expense",
        help="Is true if the order line comes from an expense or a vendor bill",
    )

    # Both constraints below also reference `price_unit`/`product_qty`/
    # `product_uom_qty`, which this mixin does not declare -- they come from
    # `mixin.order.line.amount`. A model inheriting `mixin.order.line.fields`
    # without also inheriting `mixin.order.line.amount` would fail table
    # creation on these columns being missing.
    _accountable_required_fields = models.Constraint(
        """CHECK(
            display_type IS NOT NULL
            OR is_downpayment
            OR (
                product_id IS NOT NULL
                AND product_uom_id IS NOT NULL
            )
        )""",
        "Missing required fields on accountable order line.",
    )
    _non_accountable_null_fields = models.Constraint(
        """CHECK(
            display_type IS NULL
            OR (
                product_id IS NULL
                AND (price_unit IS NULL OR price_unit = 0)
                AND product_uom_id IS NULL
                AND (product_qty IS NULL OR product_qty = 0)
                AND (product_uom_qty IS NULL OR product_uom_qty = 0)
            )
        )""",
        "Forbidden values on non-accountable order line",
    )

    def _run_check_registry(self, method_names, *args):
        for method_name in method_names:
            getattr(self, method_name)(*args)

    def _get_order_type(self):
        if not self._order_type:
            _debug.logic("order_type_undeclared", model=self._name)
            raise NotImplementedError(f"{self._name} must declare _order_type")
        return self._order_type

    def _domain_product_id(self):
        if self._abstract:
            return []
        return [(self._product_ok_field, "=", True)]

    def _get_merge_date_field(self):
        return

    @api.model
    def _prepare_display_type_reset_vals(self):
        return {
            "product_id": False,
            "price_unit": False,
            "product_qty": False,
            "product_uom_qty": False,
            "product_uom_id": False,
        }

    @api.model_create_multi
    def create(self, vals_list):
        nullify_vals = self._prepare_display_type_reset_vals()
        for vals in vals_list:
            # Guard the caller's own values: nullifying a section line writes the
            # derived quantity itself, which the guard would otherwise refuse.
            self._check_write_derived_quantity(vals)
            if vals.get("display_type") or self.default_get(["display_type"]).get(
                "display_type",
            ):
                vals.update(nullify_vals)
                _debug.logic("display_type_line_nullified", model=self._name)

        lines = super().create(vals_list)
        _debug.lifecycle("create", lines=lines, rows=len(vals_list))

        lines.filtered(
            lambda line: line.order_id.state == "done",
        )._hook_on_created_confirmed_lines()

        return lines

    def write(self, vals):
        self._check_write_guards(vals)
        tracked = [f for f in self._get_fields_tracked_qty() if f in vals]
        changes = self._collect_qty_changes(vals, tracked) if tracked else {}
        _debug.lifecycle("write", lines=self, fields=list(vals))
        result = super().write(vals)
        for field_name, field_changes in changes.items():
            _debug.pipeline(
                "quantity_changes_posted",
                lines=self,
                field=field_name,
                changed=len(field_changes),
            )
            self._post_quantity_changes(field_name, field_changes)
        return result

    def _get_fields_tracked_qty(self):
        return ["product_qty"]

    def _collect_qty_changes(self, vals, tracked_fields):
        precision = self.env["decimal.precision"].get_precision("Product Unit")
        changes = defaultdict(list)
        for field_name in tracked_fields:
            for line in self:
                if (
                    line.order_id.state == "done"
                    and float_compare(
                        line[field_name],
                        vals[field_name],
                        precision_digits=precision,
                    )
                    != 0
                ):
                    changes[field_name].append(
                        {
                            "line": line,
                            "old_qty": line[field_name],
                            "new_qty": vals[field_name],
                        },
                    )
        return changes

    def _post_quantity_changes(self, field_name, changes):
        return

    @api.depends("product_id", "product_id.uom_id", "product_id.uom_ids")
    def _compute_allowed_uom_ids(self):
        for line in self:
            line.allowed_uom_ids = (
                line.product_id.uom_id
                | line.product_id.uom_ids
                | line._get_extra_allowed_uoms()
            )

    def _get_extra_allowed_uoms(self):
        return self.env["uom.uom"]

    @api.depends("product_id")
    def _compute_product_uom_id(self):
        for line in self:
            if not line.product_uom_id or (
                line._origin.product_id and line._origin.product_id != line.product_id
            ):
                _debug.logic(
                    "line_uom_defaulted",
                    line=line,
                    origin_product=line._origin.product_id,
                    product=line.product_id,
                )
                line.product_uom_id = line._get_default_product_uom()

    def _get_default_product_uom(self):
        return self.product_id.uom_id

    @api.depends("product_id")
    def _compute_name(self):
        for line in self:
            if not line._name_should_be_computed():
                continue
            lang = line._get_line_description_lang()
            if lang != self.env.lang:
                line = line.with_context(lang=lang)
            line.name = line._get_line_description()

    def _get_line_description(self):
        self.check_singleton()
        if self._is_down_payment_section():
            return _("Down Payments")
        return self._get_default_line_description()

    def _is_down_payment_section(self):
        return bool(self.display_type) and self.is_downpayment

    def _name_should_be_computed(self):
        return bool(self.product_id) or self._is_down_payment_section()

    def _get_line_description_lang(self):
        return self.env.lang

    def _get_default_line_description(self):
        raise NotImplementedError(
            f"{self._name} must implement _get_default_line_description()"
        )

    @api.depends("product_id")
    def _compute_product_name_translated(self):
        for line in self:
            line.product_name_translated = line.product_id.with_context(
                lang=line._get_line_description_lang(),
            ).display_name

    def _get_warning_group(self):
        return False

    def _get_product_warn_field(self):
        return False

    def _compute_line_warn_msg(self, target_field):
        product_field = self._get_product_warn_field()
        group = self._get_warning_group()
        if not product_field or (group and not self.env.user.has_group(group)):
            setattr(self, target_field, "")
            return
        for line in self:
            setattr(line, target_field, line.product_id[product_field])

    @api.depends("product_id")
    def _compute_product_is_archived(self):
        for line in self:
            line.product_is_archived = line.product_id and not line.product_id.active

    @api.depends(
        "sequence",
        "display_type",
        "order_id.line_ids.sequence",
        "order_id.line_ids.display_type",
    )
    def _compute_parent_id(self):
        target_lines = set(self)
        for order, lines in self.grouped("order_id").items():
            if not order:
                lines.parent_id = False
                continue
            last_section = False
            last_sub = False
            for line in order.line_ids.sorted("sequence"):
                if line.display_type == "line_section":
                    last_section = line
                    if line in target_lines:
                        line.parent_id = False
                    last_sub = False
                elif line.display_type == "line_subsection":
                    if line in target_lines:
                        line.parent_id = last_section
                    last_sub = line
                elif line in target_lines:
                    line.parent_id = last_sub or last_section

    def get_line_parent_section(self):
        if not self.display_type and self.parent_id.display_type == "line_subsection":
            return self.parent_id.parent_id

        return self.parent_id

    def _check_write_guards(self, write_vals):
        self._run_check_registry(self._get_check_write_guards(), write_vals)

    def _get_check_write_guards(self):
        return [
            "_check_write_display_type",
            "_check_write_locked_order",
            "_check_write_derived_quantity",
        ]

    def _is_display_type_change_allowed(self, line, new_type):
        return False

    def _check_write_display_type(self, write_vals):
        if "display_type" not in write_vals:
            return

        new_type = write_vals.get("display_type")
        lines = self.filtered(
            lambda l: (
                l.display_type != new_type
                and not self._is_display_type_change_allowed(l, new_type)
            ),
        )
        if not lines:
            return

        _debug.logic(
            "display_type_change_refused", lines=lines, new_type=new_type or "none"
        )
        if len(lines) == 1:
            raise UserError(
                _(
                    "You cannot change the type of %(line_type)s '%(line_id)s'. "
                    "Instead, delete the current line and create a new line of the proper type.",
                    line_type=self._description.lower(),
                    line_id=self._get_line_identifier(lines[0]),
                ),
            )
        line_ids = [self._get_line_identifier(l) for l in lines[:5]]
        error_msg = ", ".join(line_ids)
        if len(lines) > 5:
            error_msg += _(" and %s more", len(lines) - 5)
        raise UserError(
            _(
                "You cannot change the type of %(count)s %(line_type)s lines (%(lines)s). "
                "Instead, delete these lines and create new lines of the proper type.",
                count=len(lines),
                line_type=self._description.lower(),
                lines=error_msg,
            ),
        )

    def _check_write_locked_order(self, write_vals):
        locked_lines = self.filtered(lambda l: l.locked)
        if not locked_lines:
            return

        protected_fields = self._get_fields_protected()
        protected_fields_modified = list(set(protected_fields) & set(write_vals.keys()))
        if not protected_fields_modified:
            return

        if "name" in protected_fields_modified and all(
            locked_lines.mapped("is_downpayment"),
        ):
            protected_fields_modified.remove("name")

        if not protected_fields_modified:
            return

        fields_info = (
            self.env["ir.model.fields"]
            .sudo()
            .search(
                [
                    ("name", "in", protected_fields_modified),
                    ("model", "=", self._name),
                ],
            )
        )
        if fields_info:
            _debug.logic(
                "write_refused",
                lines=locked_lines,
                reason="locked_order",
                fields=",".join(sorted(protected_fields_modified)),
            )
            raise UserError(
                _(
                    "It is forbidden to modify the following fields in a locked order:\n%s",
                    "\n".join(fields_info.mapped("field_description")),
                ),
            )

    def _get_fields_protected(self):
        return [
            "product_id",
            "name",
            "price_unit",
            "product_uom_id",
            "product_qty",
            "tax_ids",
            "analytic_distribution",
            "discount",
        ]

    def _get_line_identifier(self, line):
        if line.product_id:
            return line.product_id.display_name
        elif line.name:
            name = line.name.split("\n")[0]
            return name[:50] + "..." if len(name) > 50 else name
        else:
            return _("Line #%s", line.sequence or line.id)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_confirmed(self):
        lines_to_block = self._filtered_unlink_forbidden()
        if lines_to_block:
            state_description = dict(
                self._fields["state"]._description_selection(self.env),
            )
            state_label = state_description.get(
                lines_to_block[0].state,
                lines_to_block[0].state,
            )
            _debug.logic("line_unlink_refused", lines=lines_to_block, state=state_label)
            raise UserError(
                _(
                    "Cannot delete a %(line_type)s which is in state '%(state)s'.\n"
                    "Once an order is confirmed, you can't remove lines that have "
                    "been invoiced or %(verb)s (we need to track if something "
                    "gets invoiced or %(verb)s).\nSet the quantity to 0 instead.",
                    line_type=self._description.lower(),
                    state=state_label,
                    verb=self._transfer_verb,
                ),
            )

    def _filtered_unlink_forbidden(self):
        return self.filtered(
            lambda line: line.state == "done" and not line.display_type,
        )

    qty_transferred_method = fields.Selection(
        selection=[
            ("manual", "Manual"),
            ("analytic", "Analytic From Expenses"),
            ("stock_move", "Stock Moves"),
        ],
        string="Transferred Qty Method",
        compute="_compute_qty_transferred_method",
        precompute=True,
        store=True,
        help="Method used to compute the transferred quantity:\n"
        "  - Manual: set manually on the line\n"
        "  - Analytic: sum of analytic line unit amounts\n"
        "  - Stock Moves: from confirmed pickings\n",
    )
    qty_transferred = fields.Float(
        string="Transferred Qty",
        digits="Product Unit",
        compute="_compute_qty_transferred",
        store=True,
        copy=False,
        readonly=False,
    )
    qty_to_transfer = fields.Float(
        digits="Product Unit",
        copy=False,
    )
    qty_transferred_at_date = fields.Float(
        string="Transferred",
        digits="Product Unit",
        compute="_compute_qty_transferred_at_date",
    )

    @api.depends("is_expense", "product_id")
    def _compute_qty_transferred_method(self):
        for line in self:
            _debug.logic(
                "qty_transferred_method",
                line=line,
                expense=line.is_expense,
                product_type=line.product_type or "none",
            )
            if line.is_expense:
                line.qty_transferred_method = "analytic"
            elif line.product_id and line.product_type == "service":
                line.qty_transferred_method = "manual"
            elif line.product_id and line.product_type == "consu":
                line.qty_transferred_method = "stock_move"
            else:
                line.qty_transferred_method = False

    @api.depends("qty_transferred_method")
    def _compute_qty_transferred(self):
        lines_manual = self.filtered(
            lambda line: line.qty_transferred_method == "manual",
        )
        lines_manual.qty_transferred = 0.0

    @api.depends_context("accrual_entry_date")
    @api.depends("qty_transferred")
    def _compute_qty_transferred_at_date(self):
        if not self._date_in_the_past():
            _debug.logic("qty_at_date", lines=self, by="current_quantity")
            for line in self:
                line.qty_transferred_at_date = line.qty_transferred
            return
        transferred_quantities = self._prepare_qty_transferred()
        for line in self:
            line.qty_transferred_at_date = transferred_quantities[line]

    def _prepare_qty_transferred(self):
        transferred_qties = defaultdict(float)
        for line in self:
            if line.qty_transferred_method == "manual":
                transferred_qties[line] = line.qty_transferred or 0.0
            else:
                transferred_qties[line] = 0.0
        return transferred_qties

    def _is_invoiced_on_transferred(self):
        return False

    def _assert_transferred_uom_convertible(self):
        for line in self.filtered(lambda l: l._is_invoiced_on_transferred()):
            try:
                line.with_context(uom_reconcile_strict=True)._prepare_qty_transferred()
            except UserError as error:
                _debug.logic(
                    "transferred_uom_not_convertible",
                    line=line,
                    uom=line.product_uom_id,
                )
                raise UserError(
                    _(
                        "Cannot invoice “%(line)s”: its transferred "
                        "(delivered/received) quantity relies on a unit of "
                        "measure conversion that is not possible, so the line "
                        "cannot be sized for invoicing. Align the units of "
                        "measure on the order line and its transfers, then try "
                        "again.\n\n%(detail)s",
                        line=line.display_name,
                        detail=error.args[0] if error.args else "",
                    )
                ) from error

    @api.model
    def _date_in_the_past(self):
        if "accrual_entry_date" not in self.env.context:
            return False
        accrual_date = fields.Date.from_string(self.env.context["accrual_entry_date"])
        return bool(accrual_date) and accrual_date < fields.Date.today()

    def _filtered_to_check_analytic_distribution(self):
        return self.filtered(lambda line: not line.display_type)

    def _check_analytic_distribution(self):
        business_domain = self._analytic_business_domain
        _debug.pipeline(
            "analytic_distribution_checked",
            lines=self,
            business_domain=business_domain or "none",
        )
        for line in self._filtered_to_check_analytic_distribution():
            line._check_distribution(
                product=line.product_id.id,
                business_domain=business_domain,
                company_id=line.company_id.id,
            )

    def _hook_on_created_confirmed_lines(self):
        if self.env.context.get("no_log_for_new_lines"):
            _debug.logic("extra_lines_not_logged", lines=self, reason="context_opt_out")
            return

        lines_by_order = defaultdict(self.browse)
        for line in self:
            if line.product_id:
                lines_by_order[line.order_id] += line

        for order, order_lines in lines_by_order.items():
            count = len(order_lines)
            if count == 1:
                msg = _("Extra line with %s", order_lines.product_id.display_name)
            elif count <= CHATTER_PRODUCT_LIST_THRESHOLD:
                product_list = (
                    "<ul>"
                    + "".join(
                        f"<li>{p}</li>"
                        for p in order_lines.mapped("product_id.display_name")
                    )
                    + "</ul>"
                )
                msg = _(
                    "Added %(count)s extra lines: %(products)s",
                    count=count,
                    products=product_list,
                )
            else:
                msg = _(
                    "Added %(count)s extra lines to this %(order_type)s",
                    count=count,
                    order_type=order._description.lower(),
                )
            _debug.lifecycle("extra_lines_logged", order=order, lines=order_lines)
            order.message_post(body=msg)

    def _get_product_catalog_lines_data(self, **kwargs):
        if len(self) == 1:
            return self._get_catalog_single_line_data(**kwargs)
        elif self:
            self.product_id.check_singleton()
            data = self[0]._get_catalog_multi_line_data(**kwargs)
            data["quantity"] = sum(
                self.mapped(
                    lambda line: line.product_uom_id._get_quantity_report(
                        qty=line.product_qty,
                        to_unit=line.product_id.uom_id,
                    ),
                ),
            )
            data["readOnly"] = True
            _debug.logic("catalog_line_data", lines=self, by="multi_line")
            return data
        return {"quantity": 0}

    def _get_catalog_single_line_data(self, **kwargs):
        raise NotImplementedError(
            f"{self._name} must implement _get_catalog_single_line_data()"
        )

    def _get_catalog_multi_line_data(self, **kwargs):
        raise NotImplementedError(
            f"{self._name} must implement _get_catalog_multi_line_data()"
        )

    @api.readonly
    def action_add_from_catalog(self):
        order_model = self._fields["order_id"].comodel_name
        order = self.env[order_model].browse(self.env.context.get("order_id"))
        return order.with_context(child_field="line_ids").action_add_from_catalog()

    def action_view_order(self):
        self.check_singleton()
        return {
            "type": "ir.actions.act_window",
            "res_model": self._fields["order_id"].comodel_name,
            "res_id": self.order_id.id,
            "view_mode": "form",
        }
