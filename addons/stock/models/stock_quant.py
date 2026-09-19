import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Domain
from odoo.tools import SQL

from ..tools import debug_log as dbg
from ..tools.reservation import RemovalStrategy

_logger = logging.getLogger(__name__)

CORE_REMOVAL_STRATEGIES = {
    "fifo": RemovalStrategy(
        order="in_date ASC, id",
        sort_key=lambda quant: (quant.in_date, quant.id),
    ),
    "lifo": RemovalStrategy(
        order="in_date DESC, id DESC",
        sort_key=lambda quant: (quant.in_date, quant.id),
        reverse=True,
    ),
    "closest": RemovalStrategy(
        order=False,
        sort_key=lambda quant: quant.id,
        sorts_by_location=True,
    ),
    "least_packages": RemovalStrategy(
        order="in_date ASC, id",
        sort_key=lambda quant: (quant.in_date, quant.id),
        narrows_to_packages=True,
    ),
}


class StockQuant(models.Model):
    _name = "stock.quant"
    _description = "Quants"
    _rec_name = "product_id"
    _rec_names_search = ["location_id", "lot_id", "package_id", "owner_id"]
    _search_visibility_fields = ()

    location_id = fields.Many2one(
        comodel_name="stock.location",
        index=True,
        required=True,
        domain=lambda self: self._domain_location_id(),
        ondelete="restrict",
        bypass_search_access=True,
    )
    company_id = fields.Many2one(  # noqa: E8529  index (product_id, location_id, lot_id, package_id, owner_id, company_id)
        related="location_id.company_id",
        string="Company",
        store=True,
        readonly=True,
    )
    warehouse_id = fields.Many2one(
        comodel_name="stock.warehouse",
        related="location_id.warehouse_id",
    )
    storage_category_id = fields.Many2one(related="location_id.storage_category_id")
    cyclic_inventory_frequency = fields.Integer(
        related="location_id.cyclic_inventory_frequency"
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        required=True,
        domain=lambda self: self._domain_product_id(),
        ondelete="restrict",
        check_company=True,
    )
    product_tmpl_id = fields.Many2one(
        comodel_name="product.template",
        related="product_id.product_tmpl_id",
        string="Product Template",
    )
    is_favorite = fields.Boolean(related="product_tmpl_id.is_favorite")
    product_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        related="product_id.uom_id",
        string="Unit",
        readonly=True,
    )
    tracking = fields.Selection(
        related="product_id.tracking",
        readonly=True,
    )
    product_categ_id = fields.Many2one(related="product_tmpl_id.categ_id")
    lot_id = fields.Many2one(
        comodel_name="stock.lot",
        string="Lot/Serial Number",
        index=True,
        domain=lambda self: self._domain_lot_id(),
        ondelete="restrict",
        check_company=True,
    )
    lot_properties = fields.Properties(
        related="lot_id.lot_properties",
        definition="product_id.lot_properties_definition",
        readonly=True,
    )
    sn_duplicated = fields.Boolean(
        string="Duplicated Serial Number",
        compute="_compute_sn_duplicated",
        help="If the same SN is in another Quant",
    )
    package_id = fields.Many2one(
        comodel_name="stock.package",
        index=True,
        domain="['|', ('location_id', '=', location_id), '&', ('location_id', '=', False), ('quant_ids', '=', False)]",
        ondelete="restrict",
        check_company=True,
        help="The package containing this quant",
    )
    owner_id = fields.Many2one(
        comodel_name="res.partner",
        index="btree_not_null",
        check_company=True,
        help="This is the owner of the quant",
    )
    # No `digits`: these hold a quantity normalised into the product's unit,
    # which nobody chose, so "Product Unit" precision would re-grid it and
    # store a 2 g receipt of a kilogram product as 0.00 (c348d72fecfe).
    quantity = fields.Float(
        min_display_digits="Product Unit",
        default=0.0,
        readonly=True,
        required=True,
        help="Quantity of products in this quant, in the default unit of measure of the product",
    )
    reserved_quantity = fields.Float(
        min_display_digits="Product Unit",
        default=0.0,
        readonly=True,
        required=True,
        help="Quantity of reserved products in this quant, in the default unit of measure of the product",
    )
    available_quantity = fields.Float(
        min_display_digits="Product Unit",
        compute="_compute_available_quantity",
        help="On hand quantity which hasn't been reserved on a transfer, in the default unit of measure of the product",
    )
    in_date = fields.Datetime(
        string="Incoming Date",
        default=fields.Datetime.now,
        readonly=True,
        required=True,
    )
    on_hand = fields.Boolean(
        search="_search_on_hand",
        store=False,
    )
    date_last_movement = fields.Datetime(
        string="Last Movement",
        compute="_compute_last_movement",
        help="Date of the most recent done move line that took goods out of, or "
        "brought goods into, this quant. Inventory adjustments do not count: a "
        "cycle count is not a movement (see Last Count Date for those).",
    )
    days_since_last_movement = fields.Integer(
        string="Days Static",
        compute="_compute_last_movement",
        search="_search_days_since_last_movement",
        help="Days the goods in this quant have sat untouched. Counted from the "
        "incoming date when no movement has ever matched the quant.",
    )

    inventory_quantity = fields.Float(
        string="Counted",
        digits="Product Unit",
        help="The product's counted quantity.",
    )
    inventory_quantity_auto_apply = fields.Float(
        string="Inventoried Quantity",
        digits="Product Unit",
        compute="_compute_inventory_quantity_auto_apply",
        inverse="_inverse_inventory_quantity_auto_apply",
        groups="stock.group_stock_manager",
    )
    inventory_diff_quantity = fields.Float(
        string="Difference",
        digits="Product Unit",
        compute="_compute_inventory_diff_quantity",
        store=True,
        readonly=True,
        help="Indicates the gap between the product's theoretical quantity and its counted quantity.",
    )
    inventory_date = fields.Date(
        string="Scheduled",
        compute="_compute_inventory_date",
        store=True,
        readonly=False,
        help="Next date the On Hand Quantity should be counted.",
    )
    last_count_date = fields.Date(
        compute="_compute_last_count_date",
        help="Last time the Quantity was Updated",
    )
    inventory_quantity_set = fields.Boolean(
        compute="_compute_inventory_quantity_set",
        store=True,
        readonly=False,
    )
    is_outdated = fields.Boolean(
        string="Quantity has been moved since last count",
        compute="_compute_is_outdated",
        search="_search_is_outdated",
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Assigned To",
        domain=lambda self: [
            ("all_group_ids", "in", self.env.ref("stock.group_stock_user").id)
        ],
        help="User assigned to do product count.",
    )

    _quant_merge_idx = models.Index(
        "(product_id, location_id, lot_id, package_id, owner_id, company_id)"
    )

    @api.constrains("location_id")
    def _check_location_id(self):
        for quant in self:
            if quant.location_id.usage == "view":
                raise ValidationError(
                    _(
                        'You cannot take products from or deliver products to a location of type "view" (%s).',
                        quant.location_id.name,
                    )
                )

    @api.constrains("product_id")
    def _check_product_id(self):
        non_storable = self.product_id.filtered(lambda p: not p.is_storable)
        if non_storable:
            raise ValidationError(
                _(
                    "Quants cannot be created for consumables or services: %s",
                    ", ".join(non_storable.mapped("display_name")),
                )
            )

    @api.constrains("lot_id", "product_id")
    def _check_lot_id(self):
        for quant in self:
            if quant.lot_id.product_id and quant.lot_id.product_id != quant.product_id:
                raise ValidationError(
                    _(
                        "The Lot/Serial number (%s) is linked to another product.",
                        quant.lot_id.name,
                    )
                )

    def _check_quantity(self):
        sn_quants = self.filtered(
            lambda q: (
                q.product_id.tracking == "serial"
                and q.location_id.usage != "inventory"
                and q.lot_id
            )
        )
        if not sn_quants:
            return
        domain = [
            ("product_id", "in", sn_quants.product_id.ids),
            ("location_id", "in", sn_quants.location_id.ids),
            ("lot_id", "in", sn_quants.lot_id.ids),
        ]
        groups = self._read_group(
            domain,
            ["product_id", "location_id", "lot_id"],
            ["quantity:sum"],
        )
        for product, _location, lot, qty in groups:
            if product.uom_id.compare(abs(qty), 1) <= 0:
                continue
            if product.uom_id.compare(qty, 0) > 0:
                raise ValidationError(
                    _(
                        "The serial number has already been assigned: \n Product: %(product)s, Serial Number: %(serial_number)s",
                        product=product.display_name,
                        serial_number=lot.name,
                    )
                )
            raise ValidationError(
                _(
                    "This serial number is at a negative quantity, so it has been"
                    " taken out more times than it was brought in: \n Product:"
                    " %(product)s, Serial Number: %(serial_number)s",
                    product=product.display_name,
                    serial_number=lot.name,
                )
            )

    @api.model
    def _get_serial_number_warning(
        self,
        product_id,
        lot_id,
        company_id,
        source_location_id=None,
        ref_doc_location_id=None,
    ):
        message = None
        recommended_location = None
        if product_id.tracking == "serial":
            internal_domain = Domain("location_id.usage", "in", ("internal", "transit"))
            if lot_id.company_id:
                internal_domain &= Domain("company_id", "=", company_id.id)
            quants = self.env["stock.quant"].search(
                Domain.AND(
                    (
                        Domain("product_id", "=", product_id.id),
                        Domain("lot_id", "in", lot_id.ids),
                        Domain("quantity", "!=", 0),
                        Domain("location_id.usage", "=", "customer") | internal_domain,
                    ),
                ),
            )
            sn_locations = quants.mapped("location_id")
            if quants:
                if not source_location_id:
                    message = _(
                        "The Serial Number (%(serial_number)s) is already used in location(s): %(location_list)s.\n\n"
                        "Is this expected? For example, this can occur if a delivery operation is validated "
                        "before its corresponding receipt operation is validated. In this case the issue will be solved "
                        "automatically once all steps are completed. Otherwise, the serial number should be corrected to "
                        "prevent inconsistent data.",
                        serial_number=lot_id.name,
                        location_list=sn_locations.mapped("display_name"),
                    )

                elif source_location_id and source_location_id not in sn_locations:
                    recommended_location = self.env["stock.location"]
                    if ref_doc_location_id:
                        for location in sn_locations:
                            if location._is_child_of(ref_doc_location_id):
                                recommended_location = location
                                break
                    else:
                        for location in sn_locations:
                            if location.usage != "customer":
                                recommended_location = location
                                break
                    if (
                        recommended_location
                        and recommended_location.company_id == company_id
                    ):
                        message = _(
                            "Serial number (%(serial_number)s) is not located in %(source_location)s, but is located in location(s): %(other_locations)s.\n\n"
                            "Source location for this move will be changed to %(recommended_location)s",
                            serial_number=lot_id.name,
                            source_location=source_location_id.display_name,
                            other_locations=sn_locations.mapped("display_name"),
                            recommended_location=recommended_location.display_name,
                        )
                    else:
                        message = _(
                            "Serial number (%(serial_number)s) is not located in %(source_location)s, but is located in location(s): %(other_locations)s.\n\n"
                            "Please correct this to prevent inconsistent data.",
                            serial_number=lot_id.name,
                            source_location=source_location_id.display_name,
                            other_locations=sn_locations.mapped("display_name"),
                        )
                        recommended_location = None
        return message, recommended_location

    @dbg.timed
    @api.model_create_multi
    def create(self, vals_list):
        dbg.lifecycle.debug(
            "stock.quant.create: %d vals, keys=%s, inventory_mode=%s",
            len(vals_list),
            dbg.vals_keys(vals_list),
            self._is_inventory_mode(),
        )

        def _add_to_cache(quant):
            if "quants_cache" in self.env.context:
                self.env.context["quants_cache"][
                    quant.product_id.id,
                    quant.location_id.id,
                    quant.lot_id.id,
                    quant.package_id.id,
                    quant.owner_id.id,
                ] |= quant

        is_inventory_mode = self._is_inventory_mode()
        allowed_fields = self._get_inventory_fields_create()
        results = [self.env["stock.quant"]] * len(vals_list)
        plain_vals = []
        counted_by_quant = {}
        for index, vals in enumerate(vals_list):
            if is_inventory_mode and any(
                f in vals
                for f in ["inventory_quantity", "inventory_quantity_auto_apply"]
            ):
                quant, created = self._create_inventory_quant(vals, allowed_fields)
                first = counted_by_quant.get(quant.id)
                if first is not None:
                    raise UserError(
                        _(
                            "Lines %(first)s and %(second)s both count the same"
                            " quant (%(quant)s). Merge them into a single line:"
                            " a quant has one counted quantity, not two.",
                            first=first + 1,
                            second=index + 1,
                            quant=quant.display_name,
                        )
                    )
                counted_by_quant[quant.id] = index
                dbg.logic.debug(
                    "create: inventory vals %d -> quant %s (created=%s)",
                    index,
                    quant.id,
                    created,
                )
                if created:
                    _add_to_cache(quant)
                results[index] = quant
            else:
                if "inventory_quantity" not in vals:
                    vals["inventory_quantity_set"] = vals.get(
                        "inventory_quantity_set", False
                    )
                plain_vals.append((index, vals))
        if plain_vals:
            plain_records = super().create([vals for _index, vals in plain_vals])
            dbg.lifecycle.debug(
                "stock.quant.create: created %s", dbg.rec(plain_records)
            )
            for (index, _vals), quant in zip(plain_vals, plain_records, strict=True):
                _add_to_cache(quant)
                results[index] = quant
            if is_inventory_mode:
                plain_records.filtered("company_id")._check_company()
        return self.env["stock.quant"].concat(*results)

    @dbg.timed
    def write(self, vals):
        dbg.lifecycle.debug(
            "stock.quant.write on %s: keys=%s", dbg.rec(self), dbg.keys(vals)
        )
        forbidden_fields = set(self._get_forbidden_fields_write())
        if self._is_inventory_mode() and forbidden_fields.intersection(vals):
            if self.filtered(lambda quant: quant.location_id.usage != "inventory"):
                raise UserError(
                    _("Quant's editing is restricted, you can't do this operation.")
                )
            dbg.logic.debug(
                "write: inventory mode drops forbidden keys %s",
                sorted(forbidden_fields.intersection(vals)),
            )
            vals = {
                name: value
                for name, value in vals.items()
                if name not in forbidden_fields
            }
            if not vals:
                return True
        return super().write(vals)

    def copy(self, default=None):
        raise UserError(_("You cannot duplicate stock quants."))

    @api.ondelete(at_uninstall=False)
    def _unlink_except_wrong_permission(self):
        if not self.env.is_superuser():
            if not self.env.user.has_group("stock.group_stock_manager"):
                raise UserError(
                    _(
                        "Quants are auto-deleted when appropriate. If you must manually delete them, please ask a stock manager to do it."
                    )
                )
            dbg.lifecycle.debug(
                "manual unlink of %s by a stock manager: zeroing through inventory",
                dbg.rec(self),
            )
            self = self.with_context(inventory_mode=True)
            self.inventory_quantity = 0
            self._apply_inventory()

    @api.model
    def name_create(self, name):
        raise UserError(
            _(
                "A quant is identified by its product, location, lot, package and"
                " owner, so it cannot be created from a name alone."
            )
        )

    def _load_records_create(self, values):
        company_user = self.env.company
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", company_user.id)], limit=1
        )
        for value in values:
            if "location_id" not in value:
                value["location_id"] = warehouse.lot_stock_id.id
        return super(
            StockQuant, self.with_context(inventory_mode=True)
        )._load_records_create(values)

    def _load_records_write(self, values):
        return super(
            StockQuant, self.with_context(inventory_mode=True)
        )._load_records_write(values)

    def _get_domain_stock_user(self, domain):
        return domain if self.env.user.has_group("stock.group_stock_user") else "[]"

    def _domain_location_id(self):
        return self._get_domain_stock_user(
            "[('usage', 'in', ['internal', 'transit'])] if context.get('inventory_mode') else []"
        )

    def _domain_lot_id(self):
        return self._get_domain_stock_user(
            "[] if not context.get('inventory_mode') else"
            " [('product_id', '=', context.get('active_id', False))] if context.get('active_model') == 'product.product' else"
            " [('product_id.product_tmpl_id', '=', context.get('active_id', False))] if context.get('active_model') == 'product.template' else"
            " [('product_id', '=', product_id)]"
        )

    def _domain_product_id(self):
        return self._get_domain_stock_user(
            "[] if not context.get('inventory_mode') else"
            " [('is_storable', '=', True), ('product_tmpl_id', 'in', context.get('product_tmpl_ids', []) + [context.get('product_tmpl_id', 0)])] if context.get('product_tmpl_ids') or context.get('product_tmpl_id') else"
            " [('is_storable', '=', True)]"
        )

    @api.depends("quantity", "reserved_quantity")
    def _compute_available_quantity(self):
        for quant in self:
            quant.available_quantity = quant.quantity - quant.reserved_quantity

    @api.depends("lot_id")
    def _compute_sn_duplicated(self):
        self.sn_duplicated = False
        domain = [
            ("tracking", "=", "serial"),
            ("lot_id", "in", self.lot_id.ids),
            ("quantity", ">", 0),
            ("location_id.usage", "in", ["internal", "transit"]),
        ]
        results = self._read_group(domain, ["lot_id"], having=[("__count", ">", 1)])
        duplicated_sn_ids = {lot.id for [lot] in results}
        self.filtered(lambda q: q.lot_id.id in duplicated_sn_ids).sn_duplicated = True

    @api.depends("location_id", "lot_id", "package_id", "owner_id")
    @api.depends_context("formatted_display_name")
    def _compute_display_name(self):
        formatted = self.env.context.get("formatted_display_name")
        for record in self:
            if not record.id:
                record.display_name = ""
            elif formatted:
                name = f"{record.location_id.name}"
                if record.package_id:
                    name += f"\t--{record.package_id.display_name}--"
                if record.lot_id:
                    name += (
                        " " if record.package_id else "\t"
                    ) + f"--{record.lot_id.name}--"
                record.display_name = name
            else:
                name = [record.location_id.display_name]
                if record.lot_id:
                    name.append(record.lot_id.name)
                if record.package_id:
                    name.append(record.package_id.display_name)
                if record.owner_id:
                    name.append(record.owner_id.name)
                record.display_name = " - ".join(name)

    def _search(self, domain, *args, **kwargs):
        domain = Domain(domain).map_conditions(
            lambda condition: (
                Domain("lot_id", "any", [condition])
                if condition.field_expr.startswith("lot_properties.")
                else condition
            )
        )
        return super()._search(domain, *args, **kwargs)

    def _search_on_hand(self, operator, value):
        if operator != "in":
            return NotImplemented
        return self.env["stock.location"]._get_domains_quantity_from_context()[0]

    def _read_group_select(self, aggregate_spec, query):
        if aggregate_spec == "inventory_quantity:sum" and self.env.context.get(
            "inventory_report_mode"
        ):
            return SQL("NULL")
        if aggregate_spec == "available_quantity:sum":
            sql_quantity = self._read_group_select("quantity:sum", query)
            sql_reserved_quantity = self._read_group_select(
                "reserved_quantity:sum", query
            )
            return SQL("%s - %s", sql_quantity, sql_reserved_quantity)
        if aggregate_spec == "inventory_quantity_auto_apply:sum":
            return self._read_group_select("quantity:sum", query)
        return super()._read_group_select(aggregate_spec, query)

    @api.onchange("location_id", "product_id", "lot_id", "package_id", "owner_id")
    def _onchange_location_or_product_id(self):
        if not (self.product_id and self.location_id):
            return
        if self.lot_id and (
            self.tracking == "none" or self.product_id != self.lot_id.product_id
        ):
            self.lot_id = False
        quants = self.search(
            self._get_domain_gather(
                self.product_id,
                self.location_id,
                self.lot_id,
                self.package_id,
                self.owner_id,
                strict=True,
            )
        )
        self.quantity = sum(
            quants.filtered(lambda quant: quant.lot_id == self.lot_id).mapped(
                "quantity"
            )
        )
        if self.lot_id and self.tracking == "serial":
            self.inventory_quantity = 1
            self.inventory_quantity_auto_apply = 1

    @api.onchange("lot_id")
    def _onchange_serial_number(self):
        if self.lot_id and self.product_id.tracking == "serial":
            message, _recommended_location = (
                self.env["stock.quant"]
                .sudo()
                ._get_serial_number_warning(
                    self.product_id, self.lot_id, self.company_id
                )
            )
            if message:
                return {"warning": {"title": _("Warning"), "message": message}}
        return None

    @api.onchange("product_id", "company_id")
    def _onchange_product_id(self):
        if self.location_id:
            return
        if self.product_id.tracking in ["lot", "serial"]:
            previous_quants = self.env["stock.quant"].search(
                [
                    ("product_id", "=", self.product_id.id),
                    ("location_id.usage", "in", ["internal", "transit"]),
                ],
                limit=1,
                order="create_date desc",
            )
            if previous_quants:
                self.location_id = previous_quants.location_id
        if not self.location_id:
            company_id = (self.company_id and self.company_id.id) or self.env.company.id
            self.location_id = (
                self.env["stock.warehouse"]
                .search([("company_id", "=", company_id)], limit=1)
                .lot_stock_id
            )

    def action_view_stock_moves(self):
        self.check_singleton()
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "stock.stock_move_line_action"
        )
        domain = (
            (
                Domain("location_id", "=", self.location_id.id)
                | Domain("location_dest_id", "=", self.location_id.id)
            )
            & Domain("lot_id", "=", self.lot_id.id)
            & Domain("owner_id", "=", self.owner_id.id)
        )
        if self.package_id:
            domain &= Domain("package_id", "=", self.package_id.id) | Domain(
                "result_package_id", "=", self.package_id.id
            )
        action["domain"] = domain
        action["context"] = self.env["ir.actions.actions"]._eval_action_context(
            action.get("context") or "{}"
        )
        action["context"]["search_default_product_id"] = self.product_id.id
        return action

    def action_view_orderpoints(self):
        self.check_singleton()
        action = self.env["product.product"].action_view_orderpoints()
        action["domain"] = [("product_id", "=", self.product_id.id)]
        return action

    @api.model
    def action_view_quants(self):
        self = self.with_context(search_default_internal_loc=1)
        self = self._with_view_context()
        return self._prepare_action_quants(extend=True)

    @api.model
    def get_import_templates(self):
        return [
            {
                "label": _("Import Template for Inventory Adjustments"),
                "template": "/stock/static/xlsx/stock_quant.xlsx",
            }
        ]

    def init(self):
        super().init()
        self.env.cr.execute("DROP INDEX IF EXISTS stock_quant__product_id_index")
        self.env.cr.execute("DROP INDEX IF EXISTS stock_quant_product_location_idx")
