import logging
import typing
from collections import defaultdict

from odoo import api, fields, models
from odoo.exceptions import RedirectWarning, UserError, ValidationError
from odoo.tools import TransactionMemo
from odoo.tools.translate import LazyTranslate, _

from ..tools import debug_log as dbg

_logger = logging.getLogger(__name__)
_lt = LazyTranslate(__name__)


class Routing(typing.NamedTuple):
    from_loc: models.Model
    dest_loc: models.Model
    picking_type: models.Model
    action: str


class PendingWrite(typing.NamedTuple):
    toggling: models.Model
    old_resupply_whs: dict


class OwnedRecords(typing.NamedTuple):
    picking_types: models.Model
    rules: models.Model
    routes: models.Model
    config: tuple
    view_location: models.Model


ROUTE_NAMES = {
    "one_step": _lt("Receive in 1 step (stock)"),
    "two_steps": _lt("Receive in 2 steps (input + stock)"),
    "three_steps": _lt("Receive in 3 steps (input + quality + stock)"),
    "ship_only": _lt("Deliver in 1 step (ship)"),
    "pick_ship": _lt("Deliver in 2 steps (pick + ship)"),
    "pick_pack_ship": _lt("Deliver in 3 steps (pick + pack + ship)"),
}

PARTNER_LOCATION_XML_IDS = {
    "customer": "stock.stock_location_customers",
    "supplier": "stock.stock_location_suppliers",
}

PARTNER_LOCATION_MISSING = {
    "customer": _lt("Can't find any customer location."),
    "supplier": _lt("Can't find any supplier location."),
}

DEFAULT_WAREHOUSE_BY_COMPANY = TransactionMemo(
    "stock.warehouse.default_by_company", invalidated_by=("stock.warehouse",)
)

WAREHOUSE_PICKING_TYPE_CODES = {
    "in_type_id": "IN",
    "qc_type_id": "QC",
    "store_type_id": "STOR",
    "int_type_id": "INT",
    "pick_type_id": "PICK",
    "pack_type_id": "PACK",
    "out_type_id": "OUT",
    "xdock_type_id": "XD",
}


class StockWarehouse(models.Model):
    _name = "stock.warehouse"
    _description = "Warehouse"
    _order = "sequence,id"
    _check_company_auto = True

    Routing = Routing

    name = fields.Char(
        string="Warehouse",
        default=lambda self: self._default_name(),
        required=True,
    )

    active = fields.Boolean(default=True)

    sequence = fields.Integer(
        default=10,
        help="Gives the sequence of this line when displaying the warehouses.",
    )

    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        readonly=True,
        required=True,
        help="The company is automatically set from your user preferences.",
    )

    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Address",
        default=lambda self: self.env.company.partner_id,
        check_company=True,
    )

    view_location_id = fields.Many2one(
        comodel_name="stock.location",
        index=True,
        copy=False,
        required=True,
        domain="[('usage', '=', 'view'), ('company_id', '=', company_id)]",
        check_company=True,
    )

    lot_stock_id = fields.Many2one(
        comodel_name="stock.location",
        string="Location Stock",
        copy=False,
        required=True,
        domain="[('usage', '=', 'internal'), ('company_id', '=', company_id)]",
        check_company=True,
    )

    code = fields.Char(
        string="Short Name",
        size=5,
        required=True,
        help="Short name used to identify your warehouse",
    )

    route_ids = fields.Many2many(
        comodel_name="stock.route",
        relation="stock_route_warehouse",
        column1="warehouse_id",
        column2="route_id",
        string="Routes",
        copy=False,
        domain="[('warehouse_selectable', '=', True), ('company_id', 'in', [False, company_id])]",
        check_company=True,
        help="Defaults routes through the warehouse",
    )

    reception_steps = fields.Selection(
        selection=[
            ("one_step", "Receive and Store (1 step)"),
            ("two_steps", "Receive then Store (2 steps)"),
            ("three_steps", "Receive, Quality Control, then Store (3 steps)"),
        ],
        string="Incoming Shipments",
        default="one_step",
        required=True,
        help="Default incoming route to follow",
    )

    delivery_steps = fields.Selection(
        selection=[
            ("ship_only", "Deliver (1 step)"),
            ("pick_ship", "Pick then Deliver (2 steps)"),
            ("pick_pack_ship", "Pick, Pack, then Deliver (3 steps)"),
        ],
        string="Outgoing Shipments",
        default="ship_only",
        required=True,
        help="Default outgoing route to follow",
    )

    wh_input_stock_loc_id = fields.Many2one(
        comodel_name="stock.location",
        string="Input Location",
        copy=False,
        check_company=True,
    )

    wh_qc_stock_loc_id = fields.Many2one(
        comodel_name="stock.location",
        string="Quality Control Location",
        copy=False,
        check_company=True,
    )

    wh_output_stock_loc_id = fields.Many2one(
        comodel_name="stock.location",
        string="Output Location",
        copy=False,
        check_company=True,
    )

    wh_pack_stock_loc_id = fields.Many2one(
        comodel_name="stock.location",
        string="Packing Location",
        copy=False,
        check_company=True,
    )

    mto_pull_id = fields.Many2one(
        comodel_name="stock.rule",
        string="MTO rule",
        copy=False,
    )

    pick_type_id = fields.Many2one(
        comodel_name="stock.picking.type",
        copy=False,
        check_company=True,
    )

    pack_type_id = fields.Many2one(
        comodel_name="stock.picking.type",
        copy=False,
        check_company=True,
    )

    out_type_id = fields.Many2one(
        comodel_name="stock.picking.type",
        copy=False,
        check_company=True,
    )

    in_type_id = fields.Many2one(
        comodel_name="stock.picking.type",
        copy=False,
        check_company=True,
    )

    int_type_id = fields.Many2one(
        comodel_name="stock.picking.type",
        string="Internal Type",
        copy=False,
        check_company=True,
    )

    qc_type_id = fields.Many2one(
        comodel_name="stock.picking.type",
        string="Quality Control Type",
        copy=False,
        check_company=True,
    )

    store_type_id = fields.Many2one(
        comodel_name="stock.picking.type",
        string="Storage Type",
        copy=False,
        check_company=True,
    )

    xdock_type_id = fields.Many2one(
        comodel_name="stock.picking.type",
        string="Cross Dock Type",
        copy=False,
        check_company=True,
    )

    reception_route_id = fields.Many2one(
        comodel_name="stock.route",
        string="Receipt Route",
        copy=False,
        ondelete="restrict",
    )

    delivery_route_id = fields.Many2one(
        comodel_name="stock.route",
        copy=False,
        ondelete="restrict",
    )

    resupply_wh_ids = fields.Many2many(
        comodel_name="stock.warehouse",
        relation="stock_wh_resupply_table",
        column1="supplied_wh_id",
        column2="supplier_wh_id",
        string="Resupply From",
        help="Routes will be created automatically to resupply this warehouse from the warehouses ticked",
    )

    resupply_route_ids = fields.One2many(
        comodel_name="stock.route",
        inverse_name="supplied_wh_id",
        string="Resupply Routes",
        copy=False,
        help="Routes will be created for these resupply warehouses and you can select them on products and product categories",
    )

    _warehouse_name_uniq = models.Constraint(
        "unique(name, company_id)",
        "The name of the warehouse must be unique per company!",
    )

    _warehouse_code_uniq = models.Constraint(
        "unique(code, company_id)",
        "The short name of the warehouse must be unique per company!",
    )

    @api.constrains(
        "lot_stock_id",
        "wh_input_stock_loc_id",
        "wh_qc_stock_loc_id",
        "wh_output_stock_loc_id",
        "wh_pack_stock_loc_id",
    )
    def _check_sub_locations_are_inside_the_warehouse(self):
        for warehouse in self:
            view_location = warehouse.view_location_id
            if not view_location:
                continue
            for field_name in warehouse._get_sub_location_field_names():
                location = warehouse[field_name]
                if not location:
                    continue
                if not self._is_location_inside(location, view_location):
                    raise ValidationError(
                        _(
                            "%(location)s is not inside warehouse %(warehouse)s, so it "
                            "cannot be its %(field)s.",
                            location=location.display_name,
                            warehouse=warehouse.display_name,
                            field=warehouse._fields[field_name].string,
                        )
                    )

    @api.constrains("resupply_wh_ids")
    def _check_resupply_wh_ids(self):
        for warehouse in self:
            if warehouse in warehouse.resupply_wh_ids:
                raise ValidationError(
                    _(
                        "Warehouse %s cannot be resupplied by itself.",
                        warehouse.display_name,
                    )
                )

    @api.model
    def _get_default_for_company(self, company):
        # the first warehouse of a company answers every default-warehouse
        # question of a transaction; memoized until a warehouse changes
        per_company = DEFAULT_WAREHOUSE_BY_COMPANY(self.env)
        key = (company.id, self.env.uid, self.env.su)
        if key not in per_company:
            per_company[key] = self.search(
                [("company_id", "=", company.id)], limit=1
            ).id
        return self.browse(per_company[key])

    @dbg.timed
    @api.model_create_multi
    def create(self, vals_list):
        dbg.lifecycle.debug(
            "stock.warehouse.create: %d vals, keys=%s",
            len(vals_list),
            dbg.vals_keys(vals_list),
        )
        taken = {}
        chosen = defaultdict(set)
        for vals in vals_list:
            company = (
                self.env["res.company"].browse(vals["company_id"])
                if vals.get("company_id")
                else self.env.company
            )
            vals.setdefault("company_id", company.id)
            if "name" not in vals:
                vals["name"] = self._get_free_name(
                    company,
                    self._get_taken_warehouse_values(taken, "name", company, chosen),
                )
            if "code" not in vals:
                vals["code"] = self._get_free_code(
                    company,
                    self._get_taken_warehouse_values(taken, "code", company, chosen),
                )
            else:
                vals["code"] = self._normalize_code(vals["code"])
            if "partner_id" not in vals:
                vals["partner_id"] = company.partner_id.id
            chosen["name", company.id].add(vals["name"])
            chosen["code", company.id].add(vals["code"])
            if not vals.get("view_location_id"):
                loc_vals = {
                    "name": vals["code"],
                    "usage": "view",
                    "company_id": company.id,
                }
                vals["view_location_id"] = (
                    self.env["stock.location"].create(loc_vals).id
                )
            sub_locations = {
                field: values
                for field, values in self.browse()
                ._prepare_sub_location_vals(vals)
                .items()
                if not vals.get(field)
            }
            self._remove_taken_barcodes(
                "stock.location", list(sub_locations.values()), company.id
            )
            for values in sub_locations.values():
                values["location_id"] = vals["view_location_id"]
                values["company_id"] = company.id
            sub_records = (
                self.env["stock.location"]
                .with_context(active_test=False)
                .create(list(sub_locations.values()))
            )
            for field_name, location in zip(sub_locations, sub_records, strict=True):
                vals[field_name] = location.id
            dbg.lifecycle.debug(
                "create: warehouse %s/%s view location %s, sub locations %s",
                vals["name"],
                vals["code"],
                vals["view_location_id"],
                dbg.rec(sub_records),
            )

        warehouses = super().create(vals_list)
        dbg.lifecycle.debug("stock.warehouse.create: created %s", dbg.rec(warehouses))

        for warehouse in warehouses:
            with dbg.timer(
                self.env, "warehouse %s picking types + routes", warehouse.id
            ):
                new_vals = warehouse._create_or_update_picking_types()
                warehouse.write(new_vals)
                warehouse._create_or_update_route()
                warehouse._create_or_update_global_routes_rules()

                warehouse._create_resupply_routes(warehouse.resupply_wh_ids)

        for partner_id, company_id in {
            (vals["partner_id"], vals["company_id"])
            for vals in vals_list
            if vals.get("partner_id")
        }:
            self._update_partner_transit_locations(partner_id, company_id)

        self._update_multiwarehouse_group()

        return warehouses

    @dbg.timed
    def write(self, vals):
        dbg.lifecycle.debug(
            "stock.warehouse.write on %s: keys=%s", dbg.rec(self), dbg.keys(vals)
        )
        if vals.get("code"):
            vals = dict(vals, code=self._normalize_code(vals["code"]))
        self._check_company_unchanged(vals)
        warehouses = self.with_context(active_test=False)
        before = warehouses._pre_write_sync(vals)

        res = super().write(vals)

        warehouses._post_write_refresh(vals, before)
        return res

    def _check_company_unchanged(self, vals):
        if "company_id" not in vals:
            return
        for warehouse in self:
            if warehouse.company_id.id != vals["company_id"]:
                raise UserError(
                    _(
                        "Changing the company of this record is forbidden at this point, you should rather archive it and create a new one."
                    )
                )

    def _pre_write_sync(self, vals):
        warehouses = self
        warehouses._create_missing_locations(vals)

        if vals.get("reception_steps"):
            warehouses._update_location_reception(vals["reception_steps"])

        if vals.get("delivery_steps"):
            warehouses._update_location_delivery(vals["delivery_steps"])
            warehouses._update_delivery_steps_resupply(vals["delivery_steps"])

        old_resupply_whs = {}
        if vals.get("resupply_wh_ids") and not vals.get("resupply_route_ids"):
            old_resupply_whs = {
                warehouse.id: warehouse.resupply_wh_ids for warehouse in warehouses
            }

        if vals.get("partner_id"):
            if vals.get("company_id"):
                warehouses._update_partner_transit_locations(
                    vals["partner_id"], vals.get("company_id")
                )
            else:
                for warehouse in self:
                    warehouse._update_partner_transit_locations(
                        vals["partner_id"], warehouse.company_id.id
                    )

        if vals.get("code") or vals.get("name"):
            warehouses._update_name_and_code(vals.get("name"), vals.get("code"))

        toggling = (
            warehouses.filtered(lambda w: w.active != bool(vals["active"]))
            if "active" in vals
            else warehouses.browse()
        )

        if toggling or old_resupply_whs:
            dbg.logic.debug(
                "_pre_write_sync: toggling active on %s, old resupply %s",
                dbg.rec(toggling),
                {k: v.ids for k, v in old_resupply_whs.items()},
            )
        return PendingWrite(toggling=toggling, old_resupply_whs=old_resupply_whs)

    def _post_write_refresh(self, vals, before):
        warehouses = self
        triggers = self._get_fields_route_trigger()
        rule_fields = self._get_global_rule_fields()
        location_fields = frozenset(self._get_sub_location_field_names())
        changed = vals.keys()
        refresh_picking_types = (
            "code" in changed
            or not triggers.isdisjoint(changed)
            or not location_fields.isdisjoint(changed)
        )
        refresh_routes = not triggers.isdisjoint(changed)
        refresh_global = not self.env.context.get("stock_no_global_route_refresh") and (
            not triggers.isdisjoint(changed) or not rule_fields.isdisjoint(changed)
        )
        dbg.logic.debug(
            "_post_write_refresh on %s: picking_types=%s routes=%s global=%s",
            dbg.rec(warehouses),
            refresh_picking_types,
            refresh_routes,
            refresh_global,
        )

        for warehouse in warehouses:
            if refresh_picking_types:
                picking_type_vals = warehouse._create_or_update_picking_types()
                if picking_type_vals:
                    warehouse.write(picking_type_vals)
            if refresh_routes:
                warehouse._create_or_update_route()
            if refresh_global:
                warehouse._create_or_update_global_routes_rules()

            if warehouse in before.toggling:
                warehouse._update_active(vals["active"], triggers)

        if "name" in changed or "code" in changed:
            self.env["stock.picking.type"].with_context(active_test=False).search(
                [("warehouse_id", "in", warehouses.ids)]
            )._update_reference_sequences(only=None if "code" in changed else {"name"})

        for warehouse in warehouses:
            if warehouse.id in before.old_resupply_whs:
                warehouse._sync_resupply_routes(before.old_resupply_whs[warehouse.id])

        if "active" in vals:
            self._update_multiwarehouse_group()

    @dbg.timed
    def unlink(self):
        dbg.lifecycle.debug("stock.warehouse.unlink %s", dbg.rec(self))
        if not self.env.context.get("_force_unlink"):
            self._unlink_except_in_use()
        leftovers = [warehouse._get_owned_records() for warehouse in self]
        for owned in leftovers:
            dbg.lifecycle.debug(
                "unlink: owned rules %s, picking types %s, routes %s, view %s",
                dbg.rec(owned.rules),
                dbg.rec(owned.picking_types),
                dbg.rec(owned.routes),
                dbg.rec(owned.view_location),
            )

        for owned in leftovers:
            for records in owned.config:
                records.unlink()
            owned.rules.unlink()
            owned.picking_types.unlink()

        res = super().unlink()

        for owned in leftovers:
            owned.routes.unlink()
            owned.view_location.with_context(stock_unlink_subtree=True).unlink()

        self._update_multiwarehouse_group()
        return res

    def _unlink_except_in_use(self):
        owned_picking_types = (
            self.env["stock.picking.type"]
            .with_context(active_test=False)
            .search([("warehouse_id", "in", self.ids)])
        )
        self._check_archivable(owned_picking_types, deleting=True)

        locations = (
            self.env["stock.location"]
            .with_context(active_test=False)
            .search([("id", "child_of", self.view_location_id.ids)])
        )
        if not locations:
            return
        for model, field_name in (
            ("stock.quant", "location_id"),
            ("stock.move", "location_id"),
            ("stock.move", "location_dest_id"),
        ):
            record = self.env[model].search(  # noqa: E8507 - three literal (model, field) probes
                [(field_name, "in", locations.ids)], limit=1
            )
            if not record:
                continue
            raise UserError(
                _(
                    "Warehouse %s has stock or transfer records on its locations, so "
                    "it cannot be deleted. Archive it instead — its history stays "
                    "readable.",
                    self._get_one_display_name(record[field_name].warehouse_id),
                )
            )

    def _get_owned_records(self):
        self.check_singleton()
        locations = (
            self.env["stock.location"]
            .with_context(active_test=False)
            .search([("id", "child_of", self.view_location_id.id)])
        )
        picking_types = (
            self.env["stock.picking.type"]
            .with_context(active_test=False)
            .search([("warehouse_id", "=", self.id)])
        )
        rules = (
            self.env["stock.rule"]
            .with_context(active_test=False)
            .search(
                [
                    "|",
                    ("warehouse_id", "=", self.id),
                    ("picking_type_id", "in", picking_types.ids),
                ]
            )
        )
        routes = self.env["stock.route"].browse()
        for field_name in self._get_route_field_names():
            routes |= self[field_name]
        routes |= (
            self.env["stock.route"]
            .with_context(active_test=False)
            .search(
                [
                    "|",
                    ("supplied_wh_id", "=", self.id),
                    ("supplier_wh_id", "=", self.id),
                ]
            )
        )
        return OwnedRecords(
            picking_types=picking_types,
            rules=rules,
            routes=routes.filtered(lambda r: len(r.warehouse_ids) <= 1),
            config=(
                self.env["stock.putaway.rule"]
                .with_context(active_test=False)
                .search(
                    [
                        "|",
                        ("location_in_id", "in", locations.ids),
                        ("location_out_id", "in", locations.ids),
                    ]
                ),
                self.env["stock.warehouse.orderpoint"]
                .with_context(active_test=False)
                .search([("warehouse_id", "=", self.id)]),
            ),
            view_location=self.view_location_id,
        )

    def copy_data(self, default=None):
        default = dict(default or {})
        vals_list = super().copy_data(default=default)
        taken = {}
        chosen = defaultdict(set)
        for warehouse, vals in zip(self, vals_list, strict=True):
            company = warehouse.company_id
            if "name" not in default:
                vals["name"] = self._get_unique_copy_name(
                    _("%s (copy)", warehouse.name),
                    company,
                    self._get_taken_warehouse_values(taken, "name", company, chosen),
                )
            if "code" not in default:
                vals["code"] = self._get_free_code(
                    company,
                    self._get_taken_warehouse_values(taken, "code", company, chosen),
                )
            if vals.get("name"):
                chosen["name", company.id].add(vals["name"])
            if vals.get("code"):
                chosen["code", company.id].add(vals["code"])
        return vals_list

    def _default_name(self):
        return self._get_free_name(self.env.company)

    @api.onchange("company_id")
    def _onchange_company_id(self):
        group_user = self.env.ref("base.group_user")
        group_stock_multi_warehouses = self.env.ref(
            "stock.group_stock_multi_warehouses"
        )
        group_stock_multi_location = self.env.ref("stock.group_stock_multi_locations")
        if (
            group_stock_multi_warehouses not in group_user.implied_ids
            and group_stock_multi_location not in group_user.implied_ids
        ):
            return {
                "warning": {
                    "title": _("Warning"),
                    "message": _(
                        "Creating a new warehouse will automatically activate the Storage Locations setting"
                    ),
                }
            }
        return None

    @api.model
    def get_current_warehouses(self):
        return self.search_read(
            [("company_id", "in", self.env.companies.ids)],
            fields=["id", "name", "code"],
        )

    @dbg.timed
    def _update_active(self, active, reactivate_depends):
        self.check_singleton()
        dbg.lifecycle.debug("[warehouse:%s] active -> %s", self.id, active)
        PickingType = self.env["stock.picking.type"]
        picking_types = PickingType.with_context(active_test=False).search(
            [("warehouse_id", "=", self.id)]
        )
        if not active:
            self._check_archivable(picking_types)
        picking_types.write({"active": active})
        self.view_location_id.write({"active": active})

        rules = (
            self.env["stock.rule"]
            .with_context(active_test=False)
            .search([("warehouse_id", "=", self.id)])
        )
        self.route_ids.filtered(lambda r: len(r.warehouse_ids) == 1).write(
            {"active": active}
        )
        resupply_routes = self._update_resupply_route_activity(active)
        if active:
            dormant = resupply_routes.filtered(lambda route: not route.active)
            if dormant:
                dbg.logic.debug(
                    "_update_active: rules of dormant resupply routes %s stay archived",
                    dbg.rec(dormant),
                )
                rules = rules.filtered(lambda rule: rule.route_id not in dormant)
        dbg.lifecycle.debug(
            "_update_active: picking types %s, rules %s -> active=%s",
            dbg.rec(picking_types),
            dbg.rec(rules),
            active,
        )
        rules.write({"active": active})

        if active:
            values = {depend: self[depend] for depend in reactivate_depends}
            if values:
                self.write(values)
            self._update_resupply_rule_activity()

    def _check_archivable(self, picking_types, deleting=False):
        PickingType = self.env["stock.picking.type"].with_context(active_test=False)
        open_moves = self.env["stock.move"]._read_group(
            [
                ("picking_type_id", "in", picking_types.ids),
                ("state", "not in", ("done", "cancel")),
            ],
            ["picking_type_id"],
        )
        if open_moves:
            blocking = PickingType.union(
                *(picking_type for (picking_type,) in open_moves)
            )
            raise UserError(
                _(
                    "You still have ongoing operations for operation types %(operations)s in warehouse %(warehouse)s",
                    operations=blocking.mapped("name"),
                    warehouse=self._get_one_display_name(blocking.warehouse_id),
                )
            )
        locations = (
            self.env["stock.location"]
            .with_context(active_test=False)
            .search([("id", "child_of", self.view_location_id.ids)])
        )
        if not locations:
            return
        foreign = PickingType.search(
            [
                "|",
                ("default_location_src_id", "in", locations.ids),
                ("default_location_dest_id", "in", locations.ids),
                ("id", "not in", picking_types.ids),
            ]
        )
        if not foreign:
            return
        owners = (
            foreign.default_location_src_id | foreign.default_location_dest_id
        ).warehouse_id
        message = (
            _(
                "%(operations)s have default source or destination locations within warehouse %(warehouse)s, therefore you cannot delete it.",
                operations=foreign.mapped("name"),
                warehouse=self._get_one_display_name(owners),
            )
            if deleting
            else _(
                "%(operations)s have default source or destination locations within warehouse %(warehouse)s, therefore you cannot archive it.",
                operations=foreign.mapped("name"),
                warehouse=self._get_one_display_name(owners),
            )
        )
        raise UserError(message)

    def _get_one_display_name(self, candidates):
        return ((candidates & self) or self)[:1].display_name

    def _update_multiwarehouse_group(self):
        group_user = self.env.ref("base.group_user")
        group_multi_warehouses = self.env.ref("stock.group_stock_multi_warehouses")
        group_multi_locations = self.env.ref("stock.group_stock_multi_locations")
        several = bool(
            self.env["stock.warehouse"]
            .sudo()
            ._read_group(
                [("active", "=", True)],
                ["company_id"],
                aggregates=["__count"],
                having=[("__count", ">", 1)],
                limit=1,
            )
        )
        if several == (group_multi_warehouses in group_user.implied_ids):
            return
        dbg.lifecycle.debug(
            "_update_multiwarehouse_group: several=%s, toggling implied groups", several
        )
        if not several:
            group_user.sudo().write(
                {"implied_ids": [fields.Command.unlink(group_multi_warehouses.id)]}
            )
            return
        enabling_locations = group_multi_locations not in group_user.implied_ids
        group_user.sudo().write(
            {
                "implied_ids": [
                    fields.Command.link(group_multi_warehouses.id),
                    fields.Command.link(group_multi_locations.id),
                ]
            }
        )
        if enabling_locations:
            self.sudo()._update_multi_location_defaults(True)

    @api.model
    def _update_multi_location_defaults(self, enabled):
        warehouses = self.env["stock.warehouse"].with_context(active_test=True)
        if enabled:
            warehouses.search([]).int_type_id.active = True
        else:
            warehouses.search(
                [
                    ("reception_steps", "=", "one_step"),
                    ("delivery_steps", "=", "ship_only"),
                ]
            ).int_type_id.active = False
        for xml_id in (
            "stock.view_stock_location_list_2_editable",
            "stock.view_stock_location_form_editable",
        ):
            view = self.env.ref(xml_id, raise_if_not_found=False)
            if view:
                view.active = not enabled

    def _get_taken_warehouse_values(self, cache, field_name, company, chosen=None):
        key = (field_name, company.id)
        if key not in cache:
            cache[key] = self._get_existing_warehouse_values(field_name, company)
        if chosen is None:
            return cache[key]
        return cache[key] | chosen[key]

    def _get_existing_warehouse_values(self, field_name, company, taken=()):
        return set(taken) | set(
            self.env["stock.warehouse"]
            .with_context(active_test=False)
            .search([("company_id", "=", company.id)])
            .mapped(field_name)
        )

    def _get_free_name(self, company, existing=None):
        if existing is None:
            existing = self._get_existing_warehouse_values("name", company)
        if not existing:
            return company.name
        counter = len(existing) + 1
        while True:
            candidate = _(
                "%(company)s - warehouse # %(counter)s",
                company=company.name,
                counter=counter,
            )
            if candidate not in existing:
                return candidate
            counter += 1

    def _get_free_code(self, company, existing=None):
        if existing is None:
            existing = self._get_existing_warehouse_values("code", company)
        size = self._fields["code"].size
        base = self._normalize_code(company.name) or "WH"
        if base not in existing:
            return base
        for counter in range(2, 100000):
            suffix = str(counter)
            candidate = base[: size - len(suffix)] + suffix
            if candidate not in existing:
                return candidate
        raise UserError(
            _(
                "Unable to generate a unique short name for a warehouse in %s.",
                company.display_name,
            )
        )

    def _get_unique_copy_name(self, base, company, existing=None):
        if existing is None:
            existing = self._get_existing_warehouse_values("name", company)
        if base not in existing:
            return base
        counter = 2
        while True:
            candidate = "%s %s" % (base, counter)
            if candidate not in existing:
                return candidate
            counter += 1

    @api.model
    def _normalize_code(self, code):
        return (code or "").replace(" ", "").upper()[: self._fields["code"].size]

    def _get_normalized_code(self):
        self.check_singleton()
        return self._normalize_code(self.code)

    def _update_name_and_code(self, new_name=False, new_code=False):
        if new_code:
            self.view_location_id.write({"name": new_code})
            self._update_rule_names(new_code)
            self._update_location_barcodes(new_code)
        if new_name:
            self._update_route_names(new_name)

    @api.model
    def _raise_missing_warehouse(self):
        if not self.env.registry.ready:
            return
        if not self.env.user.has_group("stock.group_stock_manager"):
            raise UserError(
                self.env._(
                    "Please contact your administrator to configure your warehouse."
                )
            )
        warehouse_action = self.env.ref("stock.action_stock_warehouse")
        msg = _(
            "Please create a warehouse for company %s.", self.env.company.display_name
        )
        raise RedirectWarning(msg, warehouse_action.id, _("Go to Warehouses"))
