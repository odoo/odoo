from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare
from odoo.tools.misc import clean_context

from ..tools import debug_log as dbg
from odoo.addons.base.models.mixin_catalog import name_uniq_index


class StockScrap(models.Model):
    _name = "stock.scrap"
    _inherit = ["mixin.mail.thread"]
    _order = "id desc"
    _description = "Scrap"

    name = fields.Char(
        string="Reference",
        default=lambda self: _("New"),
        copy=False,
        readonly=True,
        required=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        required=True,
    )
    origin = fields.Char(string="Source Document")
    product_id = fields.Many2one(
        comodel_name="product.product",
        required=True,
        domain="[('type', '=', 'consu')]",
        check_company=True,
    )
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
        required=True,
        domain="[('id', 'in', allowed_uom_ids)]",
    )
    tracking = fields.Selection(
        related="product_id.tracking",
        string="Product Tracking",
        readonly=True,
    )
    lot_id = fields.Many2one(
        comodel_name="stock.lot",
        string="Lot/Serial",
        domain="[('product_id', '=', product_id)]",
        check_company=True,
    )
    package_id = fields.Many2one(
        comodel_name="stock.package",
        check_company=True,
    )
    owner_id = fields.Many2one(
        comodel_name="res.partner",
        check_company=True,
    )
    move_ids = fields.One2many(
        comodel_name="stock.move",
        inverse_name="scrap_id",
    )
    picking_id = fields.Many2one(
        comodel_name="stock.picking",
        check_company=True,
    )
    location_id = fields.Many2one(
        comodel_name="stock.location",
        string="Source Location",
        compute="_compute_location_id",
        precompute=True,
        store=True,
        readonly=False,
        required=True,
        domain="[('usage', '=', 'internal')]",
        check_company=True,
    )
    scrap_location_id = fields.Many2one(
        comodel_name="stock.location",
        compute="_compute_scrap_location_id",
        precompute=True,
        store=True,
        readonly=False,
        required=True,
        domain="[('usage', '=', 'inventory')]",
        check_company=True,
        help="Inventory-loss location the scrapped goods are moved to. Any"
        " inventory-loss location qualifies; a company can designate its"
        " dedicated scrap location by tagging it with the external id"
        " 'stock.stock_location_scrap_company_<company_id>'.",
    )
    scrap_qty = fields.Float(
        string="Quantity",
        digits="Product Unit",
        compute="_compute_scrap_qty",
        default=1.0,
        store=True,
        readonly=False,
        required=True,
    )
    state = fields.Selection(
        selection=[("draft", "Draft"), ("done", "Done")],
        string="Status",
        default="draft",
        readonly=True,
        tracking=True,
    )
    date_done = fields.Datetime(
        string="Date",
        readonly=True,
    )
    should_replenish = fields.Boolean(
        string="Replenish Quantities",
        help="Trigger replenishment for scrapped products",
    )
    scrap_reason_tag_ids = fields.Many2many(
        comodel_name="stock.scrap.reason.tag",
        string="Scrap Reason",
    )

    @api.depends(
        "product_id",
        "product_id.uom_id",
        "product_id.uom_ids",
        "product_id.seller_ids",
        "product_id.seller_ids.product_uom_id",
    )
    def _compute_allowed_uom_ids(self):
        for scrap in self:
            scrap.allowed_uom_ids = scrap.product_id._get_allowed_uoms()

    @api.depends("product_id")
    def _compute_product_uom_id(self):
        for scrap in self:
            scrap.product_uom_id = scrap.product_id.uom_id

    # `picking_id.state` belongs in this list and is deliberately absent: the
    # compute reads it, but declaring it made every write of a picking's state
    # search stock.scrap for dependents, and a kit explosion writes that state
    # once per move it creates -- measured at 3.67 queries per move against a
    # guard of 1.0 in mrp. The cost of the staleness it leaves is recorded in
    # `TestDerivedDefaults`; the cost of curing it this way was a hot path in
    # another module.
    @api.depends(
        "company_id",
        "picking_id",
        "picking_id.location_id",
        "picking_id.location_dest_id",
    )
    def _compute_location_id(self):
        company_warehouses = self.env["stock.warehouse"].search(
            [("company_id", "in", self.company_id.ids)]
        )
        if len(company_warehouses) == 0 and self.company_id:
            self.env["stock.warehouse"]._raise_missing_warehouse()
        locations_per_company = {}
        for warehouse in company_warehouses:
            locations_per_company.setdefault(
                warehouse.company_id.id, warehouse.lot_stock_id.id
            )
        for scrap in self:
            if scrap.picking_id:
                scrap.location_id = (
                    scrap.picking_id.location_dest_id
                    if scrap.picking_id.state == "done"
                    else scrap.picking_id.location_id
                )
            elif scrap.company_id:
                scrap.location_id = locations_per_company.get(
                    scrap.company_id.id, False
                )

    @api.depends("company_id")
    def _compute_scrap_location_id(self):
        locations = self.env["stock.location"].search_fetch(
            [("company_id", "in", self.company_id.ids), ("usage", "=", "inventory")],
            ["company_id"],
            order="id",
        )
        locations_per_company = {}
        for location in locations:
            locations_per_company.setdefault(location.company_id.id, location)
        for company in self.company_id:
            designated = self.env.ref(
                f"stock.stock_location_scrap_company_{company.id}",
                raise_if_not_found=False,
            )
            if (
                designated is not None
                and designated._name == "stock.location"
                and designated.usage == "inventory"
                and designated.company_id == company
                and designated.active
            ):
                locations_per_company[company.id] = designated
        for scrap in self:
            if scrap.company_id:
                scrap.scrap_location_id = locations_per_company.get(
                    scrap.company_id.id, False
                )

    @api.depends("move_ids", "move_ids.move_line_ids.quantity", "product_id")
    def _compute_scrap_qty(self):
        self.scrap_qty = 1
        for scrap in self:
            if scrap.move_ids:
                scrap.scrap_qty = scrap.move_ids[0].quantity

    @api.onchange("lot_id")
    def _onchange_serial_number(self):
        if self.product_id.tracking != "serial" or not self.lot_id:
            return None
        message, recommended_location = (
            self.env["stock.quant"]
            .sudo()
            ._get_serial_number_warning(
                self.product_id,
                self.lot_id,
                self.company_id,
                self.location_id,
                self.picking_id.location_dest_id,
            )
        )
        if not message:
            return None
        if recommended_location:
            self.location_id = recommended_location
        return {"warning": {"title": _("Warning"), "message": message}}

    @api.ondelete(at_uninstall=False)
    def _unlink_except_done(self):
        if "done" in self.mapped("state"):
            raise UserError(_("You cannot delete a scrap which is done."))

    def _prepare_move_values(self):
        self.check_singleton()
        return {
            "origin": self.origin or self.picking_id.name or self.name,
            "company_id": self.company_id.id,
            "product_id": self.product_id.id,
            "product_uom_id": self.product_uom_id.id,
            "state": "draft",
            "product_uom_qty": self.scrap_qty,
            "location_id": self.location_id.id,
            "scrap_id": self.id,
            "location_dest_id": self.scrap_location_id.id,
            "move_line_ids": [
                (
                    0,
                    0,
                    {
                        "product_id": self.product_id.id,
                        "product_uom_id": self.product_uom_id.id,
                        "quantity": self.scrap_qty,
                        "location_id": self.location_id.id,
                        "location_dest_id": self.scrap_location_id.id,
                        "package_id": self.package_id.id,
                        "owner_id": self.owner_id.id,
                        "lot_id": self.lot_id.id,
                    },
                )
            ],
            "picked": True,
            "picking_id": self.picking_id.id,
        }

    @dbg.timed
    def _action_done(self):
        dbg.pipeline.debug("stock.scrap._action_done on %s", dbg.rec(self))
        self._check_company()
        already_done = self.filtered(lambda s: s.state == "done")
        if already_done:
            raise UserError(
                _(
                    "The following scrap orders are already done and cannot be "
                    "validated again: %s",
                    ", ".join(already_done.mapped("name")),
                )
            )
        self._update_names()
        moves = self.env["stock.move"]
        for scrap in self:
            moves |= scrap._create_scrap_move()
        dbg.pipeline.debug("scrap -> stock.move._action_done %s", dbg.rec(moves))
        moves.with_context(is_scrap=True)._action_done()
        self.write({"state": "done", "date_done": fields.Datetime.now()})
        for scrap in self.filtered("should_replenish"):
            dbg.pipeline.debug("[scrap:%s] replenishing %s", scrap.id, scrap.scrap_qty)
            scrap._replenish_scrapped_quantity()
        return True

    def _check_shortfall_is_not_an_unnamed_lot(self):
        self.check_singleton()
        if self.product_id.tracking == "none" or self.lot_id:
            return
        under_lots = self.env["stock.quant"].search(
            [
                ("product_id", "=", self.product_id.id),
                ("location_id", "child_of", self.location_id.id),
                ("lot_id", "!=", False),
                ("quantity", ">", 0),
            ],
        )
        if not under_lots:
            return
        raise UserError(
            _(
                "There is no untracked stock of %(product)s in %(location)s to "
                "scrap, but %(quantity)s under lot/serial numbers: %(lots)s.\n"
                "Pick the one you mean to scrap.",
                product=self.product_id.display_name,
                location=self.location_id.display_name,
                quantity=sum(under_lots.mapped("quantity")),
                lots=", ".join(sorted(under_lots.lot_id.mapped("name"))),
            ),
        )

    def _update_names(self):
        for scrap in self:
            name = (
                self.env["ir.sequence"]
                .with_company(scrap.company_id)
                .next_by_code("stock.scrap")
            )
            if not name:
                raise UserError(
                    _(
                        "No scrap sequence is configured for %(company)s, so this "
                        "scrap cannot be given a reference. Create an "
                        "ir.sequence with code 'stock.scrap' for it.",
                        company=scrap.company_id.display_name,
                    ),
                )
            scrap.name = name

    def _create_scrap_move(self):
        self.check_singleton()
        return self.env["stock.move"].create(self._prepare_move_values())

    def _replenish_scrapped_quantity(self, values=False):
        self.check_singleton()
        values = values or {}
        self.with_context(clean_context(self.env.context)).env["stock.rule"].run(
            [
                self.env["stock.rule"].Procurement(
                    self.product_id,
                    self.scrap_qty,
                    self.product_uom_id,
                    self.location_id,
                    self.name,
                    self.name,
                    self.company_id,
                    values,
                )
            ]
        )

    def action_get_stock_picking(self):
        action = self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
            "stock.action_picking_tree_all"
        )
        action["domain"] = [("id", "=", self.picking_id.id)]
        return action

    def action_get_stock_move_lines(self):
        action = self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
            "stock.stock_move_line_action"
        )
        action["domain"] = [("move_id", "in", self.move_ids.ids)]
        return action

    def _is_available_qty_check_required(self):
        return self.product_id.is_storable

    def has_available_qty(self):
        self.check_singleton()
        if not self._is_available_qty_check_required():
            return True

        precision = self.env["decimal.precision"].get_precision("Product Unit")
        available_qty = self.with_context(
            location=self.location_id.id,
            lot_id=self.lot_id.id,
            package_id=self.package_id.id,
            owner_id=self.owner_id.id,
            strict=True,
        ).product_id.qty_available
        scrap_qty = self.product_uom_id._get_quantity_in_unit(
            self.scrap_qty, self.product_id.uom_id
        )
        dbg.logic.debug(
            "[scrap:%s] has_available_qty: available %s vs scrap %s at %s",
            self.id,
            available_qty,
            scrap_qty,
            self.location_id.id,
        )
        return float_compare(available_qty, scrap_qty, precision_digits=precision) >= 0

    def action_validate(self):
        self.check_singleton()
        if self.product_uom_id.is_zero(self.scrap_qty):
            raise UserError(_("You can only enter positive quantities."))
        if self.has_available_qty():
            return self._action_done()
        else:
            self._check_shortfall_is_not_an_unnamed_lot()
            ctx = dict(self.env.context)
            ctx.update(
                {
                    "default_product_id": self.product_id.id,
                    "default_location_id": self.location_id.id,
                    "default_scrap_id": self.id,
                    "default_quantity": self.product_uom_id._get_quantity_in_unit(
                        self.scrap_qty, self.product_id.uom_id
                    ),
                    "default_product_uom_name": self.product_id.uom_name,
                }
            )
            return {
                "name": _(
                    "%(product)s: Insufficient Quantity To Scrap",
                    product=self.product_id.display_name,
                ),
                "view_mode": "form",
                "res_model": "stock.warn.insufficient.qty.scrap",
                "view_id": self.env.ref(
                    "stock.stock_warn_insufficient_qty_scrap_form_view"
                ).id,
                "type": "ir.actions.act_window",
                "context": ctx,
                "target": "new",
            }


class StockScrapReasonTag(models.Model):
    _name = "stock.scrap.reason.tag"
    _description = "Scrap Reason Tag"
    _order = "sequence, id"

    name = fields.Char(
        translate=True,
        required=True,
    )
    sequence = fields.Integer(default=10)
    color = fields.Char(default="#3C3C3C")

    _name_src_uniq = name_uniq_index(
        message="Tag name already exists!",
    )
