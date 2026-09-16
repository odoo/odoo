from collections import Counter
from collections.abc import Iterable

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Domain
from odoo.tools import DOMAIN_PREDICATES

from ..tools import debug_log as dbg
from odoo.addons.stock.tools.quantity import get_domain_quantity_in_python


class StockLot(models.Model):
    _name = "stock.lot"
    _inherit = ["mixin.mail.thread", "mixin.mail.activity"]
    _description = "Lot/Serial"
    _check_company_auto = True
    _order = "name, id"

    name = fields.Char(
        string="Lot/Serial Number",
        compute="_compute_name",
        precompute=True,
        store=True,
        index="trigram",
        readonly=False,
        required=True,
        help="Unique Lot/Serial Number",
    )
    active = fields.Boolean(default=True)
    ref = fields.Char(
        string="Internal Reference",
        help="Internal reference number in case it differs from the manufacturer's lot/serial number",
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        index=True,
        required=True,
        domain="[('tracking', '!=', 'none'), ('is_storable', '=', True)] +"
        " ([('product_tmpl_id', '=', context['default_product_tmpl_id'])] if context.get('default_product_tmpl_id') else [])",
        check_company=True,
        tracking=True,
    )
    product_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        related="product_id.uom_id",
        string="Unit",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        compute="_compute_company_id",
        store=True,
        index=True,
        readonly=False,
    )
    note = fields.Html(string="Description")
    display_complete = fields.Boolean(compute="_compute_display_complete")
    quant_ids = fields.One2many(
        comodel_name="stock.quant",
        inverse_name="lot_id",
        string="Quants",
        readonly=True,
    )
    product_qty = fields.Float(
        string="On Hand Quantity",
        compute="_compute_product_qty",
        search="_search_product_qty",
    )
    delivery_ids = fields.Many2many(
        comodel_name="stock.picking",
        string="Transfers",
        compute="_compute_delivery_ids",
    )
    count_transfer_outgoing = fields.Count(
        count_of="delivery_ids",
        string="Delivery order count",
    )
    partner_ids = fields.Many2many(
        comodel_name="res.partner",
        compute="_compute_partner_ids",
        search="_search_partner_ids",
    )
    lot_properties = fields.Properties(
        definition="product_id.lot_properties_definition",
        string="Properties",
        copy=True,
    )
    location_id = fields.Many2one(
        comodel_name="stock.location",
        compute="_compute_location_id",
        inverse="_inverse_location_id",
        store=True,
        readonly=False,
        group_expand="_read_group_location_id",
        domain="[('usage', '!=', 'view')]",
    )

    _name_product_company_uniq = models.Constraint(
        "UNIQUE NULLS NOT DISTINCT (name, product_id, company_id)",
        "The combination of lot/serial number and product must be unique within a company.",
    )

    @api.constrains("name", "product_id", "company_id", "active")
    def _check_unique_lot(self):
        own_pairs = {(lot.product_id.id, lot.name) for lot in self}
        domain = [
            ("product_id", "in", self.product_id.ids),
            ("name", "in", self.mapped("name")),
        ]
        groupby = ["company_id", "product_id", "name"]
        if any(not lot.company_id for lot in self):
            self = self.sudo()
        records = self.with_context(
            skip_preprocess_gs1=True,
            active_test=False,
        )._read_group(domain, groupby, ["__count"])
        cross_lots = {}
        for company, product, name, count in records:
            if not company:
                cross_lots[(product, name)] = count
        duplicate_pairs = set()
        for company, product, name, count in records:
            if (product.id, name) not in own_pairs:
                continue
            duplicates = count
            if company:
                duplicates += cross_lots.get((product, name), 0)
            if duplicates > 1:
                duplicate_pairs.add((product, name))
        if duplicate_pairs:
            raise self._prepare_duplicate_lot_error(duplicate_pairs)

    @api.model
    def _prepare_duplicate_lot_error(self, product_name_pairs) -> ValidationError:
        error_message_lines = sorted(
            _(
                " - Product: %(product)s, Lot/Serial Number: %(lot)s",
                product=product.display_name,
                lot=name,
            )
            for product, name in product_name_pairs
        )
        return ValidationError(
            _(
                "The combination of lot/serial number and product must be unique within a company including when no company is defined.\nThe following combinations contain duplicates:\n%(error_lines)s",
                error_lines="\n".join(error_message_lines),
            ),
        )

    @api.model
    def _check_duplicate_lot_keys(self, keys, exclude_ids=None):
        keys = [key for key in keys if key[0] and key[1]]
        if not keys:
            return
        duplicates = {key for key, count in Counter(keys).items() if count > 1}
        remaining = set(keys) - duplicates
        if remaining:
            domain = [
                ("product_id", "in", [key[0] for key in remaining]),
                ("name", "in", [key[1] for key in remaining]),
            ]
            if exclude_ids:
                domain.append(("id", "not in", list(exclude_ids)))
            groups = (
                self.sudo()
                .with_context(skip_preprocess_gs1=True, active_test=False)
                ._read_group(domain, ["product_id", "name", "company_id"], ["__count"])
            )
            existing = {
                (product.id, name, company.id if company else False)
                for product, name, company, __ in groups
            }
            duplicates |= remaining & existing
        if duplicates:
            products = self.env["product.product"].browse(
                {product_id for product_id, __, __ in duplicates}
            )
            product_by_id = {product.id: product for product in products}
            raise self._prepare_duplicate_lot_error(
                {
                    (product_by_id[product_id], name)
                    for product_id, name, __ in duplicates
                }
            )

    @dbg.timed
    @api.model_create_multi
    def create(self, vals_list):
        dbg.lifecycle.debug(
            "stock.lot.create: %d vals, keys=%s",
            len(vals_list),
            dbg.vals_keys(vals_list),
        )
        lot_product_ids = {
            product_id
            for product_id in (
                *(vals.get("product_id") for vals in vals_list),
                self.env.context.get("default_product_id"),
            )
            if product_id
        }
        self._check_lots_allowed(lot_product_ids)
        self._check_duplicate_lot_keys(
            (
                vals.get("product_id"),
                vals.get("name"),
                vals.get("company_id") or False,
            )
            for vals in vals_list
        )
        return super(StockLot, self.with_context(mail_create_nosubscribe=True)).create(
            vals_list
        )

    @dbg.timed
    def write(self, vals):
        dbg.lifecycle.debug(
            "stock.lot.write on %s: keys=%s", dbg.rec(self), dbg.keys(vals)
        )
        identity_changed = any(
            field in vals for field in ("name", "product_id", "company_id")
        )
        if identity_changed:
            dbg.logic.debug("stock.lot.write: identity change, checking duplicates")
            self._check_lots_allowed(
                {vals.get("product_id"), *self.product_id.ids} - {None, False}
            )
            self._check_duplicate_lot_keys(
                [
                    (
                        vals.get("product_id", lot.product_id.id),
                        vals.get("name", lot.name),
                        vals.get("company_id", lot.company_id.id) or False,
                    )
                    for lot in self
                ],
                exclude_ids=self.ids,
            )
        if vals.get("company_id"):
            for lot in self:
                quant_companies = lot.quant_ids.filtered(
                    lambda q: q.quantity
                ).location_id.company_id
                if any(company.id != vals["company_id"] for company in quant_companies):
                    raise UserError(
                        _(
                            "You cannot change the company of a lot/serial number currently in a location belonging to another company."
                        ),
                    )
        if "product_id" in vals and any(
            vals["product_id"] != lot.product_id.id for lot in self
        ):
            move_lines = self.env["stock.move.line"].search_count(
                [("lot_id", "in", self.ids), ("product_id", "!=", vals["product_id"])],
                limit=1,
            )
            if move_lines:
                raise UserError(
                    _(
                        "You are not allowed to change the product linked to a serial or lot number "
                        "if some stock moves have already been created with that number. "
                        "This would lead to inconsistencies in your stock."
                    ),
                )
        return super().write(vals)

    def copy_data(self, default=None):
        default = default or {}
        vals_list = super().copy_data(default=default)
        if "name" not in default:
            for lot, vals in zip(self, vals_list, strict=True):
                vals["name"] = self._get_free_lot_name(
                    lot.company_id,
                    lot.product_id,
                    _("(copy of) %s", lot.name),
                )
        return vals_list

    @api.model
    def default_get(self, fields):
        context = dict(self.env.context)
        context.pop("default_company_id", False)
        return super(StockLot, self.with_context(context)).default_get(fields)

    @api.depends("product_id.company_id")
    def _compute_company_id(self):
        for lot in self:
            owner = lot.product_id.company_id
            current = lot.company_id
            if owner and current and current != owner and owner in current.parent_ids:
                # The branch below reads `self.env.company` and
                # `self.env.companies`, so it decides by WHO is computing. That
                # is defensible while the lot is being placed and indefensible
                # afterwards. Measured: a product owned by a parent company, a
                # lot created by a user allowed only in the child, gets the
                # child -- and the same row recomputed by a user allowed in
                # both silently moves to the parent. `company_id` drives
                # record-rule visibility and `check_company` on the lot's
                # quants and move lines, so that move can hide a lot from the
                # people who created it.
                #
                # A lot sitting strictly BELOW its product's owner is exactly
                # what that branch produces, so it is kept rather than
                # re-decided. Every other shape still falls through: no owner
                # clears the lot as before, an unrelated owner re-derives, and
                # an unset company is decided for the first time.
                continue
            if (
                owner
                and owner in self.env.company.parent_ids
                and owner not in self.env.companies
            ):
                lot.company_id = self.env.company
            else:
                lot.company_id = owner

    @api.depends_context("display_complete")
    def _compute_display_complete(self):
        for prod_lot in self:
            prod_lot.display_complete = bool(
                prod_lot.id or self.env.context.get("display_complete")
            )

    @api.depends("quant_ids", "quant_ids.quantity", "quant_ids.location_id")
    def _compute_location_id(self):
        for lot in self:
            quants = lot.quant_ids.filtered(
                lambda q: q.product_uom_id.compare(q.quantity, 0) > 0
            )
            lot.location_id = (
                quants.location_id if len(quants.location_id) == 1 else False
            )

    @api.depends_context(
        "owner_id",
        "package_id",
        "to_date",
        "location",
        "warehouse_id",
        "search_location",
        "search_warehouse",
        "allowed_company_ids",
        "strict",
    )
    @api.depends("quant_ids", "quant_ids.quantity")
    def _compute_product_qty(self):
        qty_by_lot = self._get_product_qty_by_lot(Domain("lot_id", "in", self.ids))
        for lot in self:
            lot.product_qty = qty_by_lot.get(lot, 0.0)

    def _inverse_location_id(self):
        for lot in self:
            quants = lot.quant_ids.filtered(
                lambda quant: quant.product_uom_id.compare(quant.quantity, 0) > 0
            )
            if len(quants.location_id) > 1:
                raise UserError(
                    _(
                        "You can only move a lot/serial to a new location if it exists in a single location."
                    ),
                )
            if not quants:
                continue
            message = _("Lot/Serial Number Relocated")
            breaking = quants._filtered_breaking_a_package()
            dbg.pipeline.debug(
                "[lot:%s] relocate to %s: breaking packages %s, intact %s",
                lot.id,
                lot.location_id.id,
                dbg.rec(breaking),
                dbg.rec(quants - breaking),
            )
            if breaking:
                breaking.move_quants(
                    location_dest_id=lot.location_id,
                    message=message,
                    unpack=True,
                )
            intact = quants - breaking
            if intact:
                intact.move_quants(
                    location_dest_id=lot.location_id,
                    message=message,
                )

    def _search_product_qty(self, operator, value):
        op = DOMAIN_PREDICATES.get(operator)
        if not op:
            return get_domain_quantity_in_python(self, "product_qty", operator, value)
        if isinstance(value, Iterable) and not isinstance(value, str):
            value = {float(v) for v in value}
        else:
            value = float(value)
        qty_by_lot = self._get_product_qty_by_lot(Domain("lot_id", "!=", False))
        ids = [lot.id for lot, qty in qty_by_lot.items() if op(qty, value)]

        if op(0.0, value):
            lots_w_qty = [lot.id for lot in qty_by_lot]
            return ["|", ("id", "in", ids), ("id", "not in", lots_w_qty)]
        return [("id", "in", ids)]

    def action_lot_open_quants(self):
        self.check_singleton()
        quants = self.with_context(search_default_lot_id=self.id, create=False)
        if self.env.user.has_group("stock.group_stock_manager"):
            quants = quants.with_context(inventory_mode=True)
        return quants.env["stock.quant"].action_view_quants()

    def _read_group_location_id(self, locations, domain):
        partner_locations = locations.search(
            [("usage", "in", ("customer", "supplier"))]
        )
        warehouses = self.env["stock.warehouse"].search([])
        return partner_locations + warehouses.lot_stock_id

    @dbg.timed
    def _get_product_qty_by_lot(self, lot_domain):
        domain_quant_loc, domain_move_in_loc, domain_move_out_loc = (
            self.env["stock.location"]
            .with_context(skip_in_progress=True)
            ._get_domains_quantity_from_context()
        )
        owner_id = self.env.context.get("owner_id")
        package_id = self.env.context.get("package_id")
        to_date = fields.Datetime.to_datetime(self.env.context.get("to_date"))
        dates_in_the_past = to_date and to_date < fields.Datetime.now()

        domain_quant = lot_domain & domain_quant_loc
        if owner_id is not None:
            domain_quant &= Domain("owner_id", "=", owner_id)
            domain_move_in_loc &= Domain("owner_id", "=", owner_id)
            domain_move_out_loc &= Domain("owner_id", "=", owner_id)
        if package_id is not None:
            domain_quant &= Domain("package_id", "=", package_id)
            domain_move_in_loc &= Domain("result_package_id", "=", package_id)
            domain_move_out_loc &= Domain("package_id", "=", package_id)
        qty_by_lot = dict(
            self.env["stock.quant"]._read_group(
                domain_quant, ["lot_id"], ["quantity:sum"]
            )
        )
        if not dates_in_the_past:
            return qty_by_lot

        domain_lot_done = lot_domain & Domain(
            [("state", "=", "done"), ("move_id.date", ">", to_date)]
        )
        move_in_qty_by_lot = dict(
            self.env["stock.move.line"]._read_group(
                domain_move_in_loc & domain_lot_done,
                ["lot_id"],
                ["quantity_product_uom:sum"],
            )
        )
        move_out_qty_by_lot = dict(
            self.env["stock.move.line"]._read_group(
                domain_move_out_loc & domain_lot_done,
                ["lot_id"],
                ["quantity_product_uom:sum"],
            )
        )
        return {
            lot: qty_by_lot.get(lot, 0.0)
            - move_in_qty_by_lot.get(lot, 0.0)
            + move_out_qty_by_lot.get(lot, 0.0)
            for lot in set(qty_by_lot)
            | set(move_in_qty_by_lot)
            | set(move_out_qty_by_lot)
        }

    @api.model
    def _get_domain_accessible_location(self):
        return [
            "|",
            ("location_id", "=", False),
            (
                "location_id",
                "any",
                self.env["stock.location"]._check_company_domain(
                    self.env.companies.ids
                ),
            ),
        ]

    def _check_lots_allowed(self, product_ids):
        active_picking_id = self.env.context.get("active_picking_id", False)
        if active_picking_id:
            picking_id = self.env["stock.picking"].browse(active_picking_id)
            if picking_id and not picking_id.picking_type_id.use_create_lots:
                raise UserError(
                    _(
                        'You are not allowed to create a lot or serial number with this operation type. To change this, go on the operation type and tick the box "Create New Lots/Serial Numbers".'
                    ),
                )
