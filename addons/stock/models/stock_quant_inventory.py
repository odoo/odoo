import logging
import math
from ast import literal_eval

from markupsafe import escape

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.tools import SQL

from ..const import INVENTORY_REFERENCE_RELOCATED
from ..tools import debug_log as dbg

_logger = logging.getLogger(__name__)


class StockQuantInventory(models.Model):
    _inherit = "stock.quant"

    @api.depends("location_id")
    def _compute_inventory_date(self):
        quants = self.filtered(
            lambda q: (
                not q.inventory_date and q.location_id.usage in ["internal", "transit"]
            )
        )
        quants._update_next_inventory_date()

    @api.depends("product_id", "location_id", "lot_id", "package_id", "owner_id")
    def _compute_last_count_date(self):
        self.last_count_date = False
        date_by_quant = self._read_move_line_dates(is_inventory=True)
        for quant in self:
            quant.last_count_date = date_by_quant.get(quant._get_move_line_match_key())

    @api.depends(
        "product_id", "location_id", "lot_id", "package_id", "owner_id", "in_date"
    )
    def _compute_last_movement(self):
        now = fields.Datetime.now()
        date_by_quant = self._read_move_line_dates(is_inventory=False)
        for quant in self:
            date_last_movement = date_by_quant.get(quant._get_move_line_match_key())
            quant.date_last_movement = date_last_movement
            dates = [d for d in (date_last_movement, quant.in_date) if d]
            quant.days_since_last_movement = (
                max(0, (now - max(dates)).days) if dates else 0
            )

    @api.depends("inventory_quantity", "inventory_quantity_set")
    def _compute_inventory_diff_quantity(self):
        for quant in self:
            if quant.inventory_quantity_set:
                quant.inventory_diff_quantity = (
                    quant.inventory_quantity - quant.quantity
                )
            else:
                quant.inventory_diff_quantity = 0

    @api.depends("inventory_quantity")
    def _compute_inventory_quantity_set(self):
        self.inventory_quantity_set = True

    @api.depends(
        "inventory_quantity",
        "inventory_quantity_set",
        "inventory_diff_quantity",
        "quantity",
        "product_id",
    )
    def _compute_is_outdated(self):
        for quant in self:
            quant.is_outdated = quant._is_outdated()

    @api.depends("quantity")
    def _compute_inventory_quantity_auto_apply(self):
        for quant in self:
            quant.inventory_quantity_auto_apply = quant.quantity

    def _search_days_since_last_movement(self, operator, value):
        if operator not in ("<", "<=", ">", ">="):
            return NotImplemented
        try:
            value = float(value)
        except TypeError, ValueError:
            return NotImplemented
        if operator in ("<=", ">"):
            days = math.floor(value) + 1
        else:
            days = math.ceil(value)
        threshold = fields.Datetime.subtract(fields.Datetime.now(), days=days)
        self.env["stock.quant"].flush_model(
            [
                "in_date",
                "product_id",
                "location_id",
                "lot_id",
                "package_id",
                "owner_id",
            ]
        )
        self.env["stock.move.line"].flush_model(
            [
                "state",
                "date",
                "move_id",
                "product_id",
                "location_id",
                "location_dest_id",
                "lot_id",
                "package_id",
                "result_package_id",
                "owner_id",
            ]
        )
        self.env["stock.move"].flush_model(["is_inventory"])
        dormant = SQL(
            """(SELECT q.id
                  FROM stock_quant q
                 WHERE q.in_date <= %(threshold)s
                   AND NOT EXISTS (
                       SELECT 1
                         FROM stock_move_line ml
                         JOIN stock_move m ON m.id = ml.move_id
                        WHERE ml.state = 'done'
                          AND m.is_inventory IS NOT TRUE
                          AND ml.date > %(threshold)s
                          AND ml.product_id = q.product_id
                          AND ml.lot_id IS NOT DISTINCT FROM q.lot_id
                          AND ml.owner_id IS NOT DISTINCT FROM q.owner_id
                          -- location and package pair up: source with source,
                          -- destination with destination. Testing the two
                          -- independently matches identities no move ever
                          -- touched -- see `_read_move_line_dates`, which this
                          -- has to agree with.
                          AND ((ml.location_id = q.location_id
                                AND ml.package_id
                                    IS NOT DISTINCT FROM q.package_id)
                               OR (ml.location_dest_id = q.location_id
                                   AND ml.result_package_id
                                       IS NOT DISTINCT FROM q.package_id))))""",
            threshold=threshold,
        )
        return [("id", "not in" if operator in ("<", "<=") else "in", dormant)]

    def _search_is_outdated(self, operator, value):
        if operator != "in":
            return NotImplemented
        self.env["stock.quant"].flush_model(
            [
                "inventory_quantity_set",
                "inventory_quantity",
                "inventory_diff_quantity",
                "quantity",
            ]
        )
        digits = self.env["decimal.precision"].get_precision("Product Unit")
        return [
            (
                "id",
                "in",
                SQL(
                    """(SELECT id FROM stock_quant
                         WHERE inventory_quantity_set = TRUE
                           AND round(COALESCE(inventory_quantity, 0)
                                     - COALESCE(inventory_diff_quantity, 0), %s)
                               != round(quantity, %s))""",
                    digits,
                    digits,
                ),
            )
        ]

    def _inverse_inventory_quantity_auto_apply(self):
        if not self._is_inventory_mode():
            return
        quant_to_inventory = self.env["stock.quant"]
        for quant in self:
            if (
                quant.product_uom_id.compare(
                    quant.quantity, quant.inventory_quantity_auto_apply
                )
                == 0
            ):
                continue
            quant.inventory_quantity = quant.inventory_quantity_auto_apply
            quant_to_inventory |= quant
        dbg.pipeline.debug(
            "auto_apply inventory on %s of %s",
            dbg.rec(quant_to_inventory),
            dbg.rec(self),
        )
        quant_to_inventory.action_apply_inventory()

    @api.onchange("inventory_quantity")
    def _onchange_inventory_quantity(self):
        if self.location_id and self.location_id.usage == "inventory":
            warning = {
                "title": _("You cannot modify inventory loss quantity"),
                "message": _(
                    "Editing quantities in an Inventory Adjustment location is forbidden,"
                    "those locations are used as counterpart when correcting the quantities."
                ),
            }
            return {"warning": warning}
        return None

    @api.model
    def action_view_inventory(self):
        self = self._with_view_context()
        if (
            not self.env["ir.config_parameter"]
            .sudo()
            .get_param("stock.skip_quant_tasks")
        ):
            self._run_maintenance_tasks()

        ctx = dict(self.env.context or {})
        ctx["no_at_date"] = True
        if self.env.user.has_group(
            "stock.group_stock_user"
        ) and not self.env.user.has_group("stock.group_stock_manager"):
            ctx["search_default_my_count"] = True
        view_id = self.env.ref("stock.view_stock_quant_list_inventory_editable").id
        return {
            "name": _("Physical Inventory"),
            "view_mode": "list",
            "res_model": "stock.quant",
            "type": "ir.actions.act_window",
            "context": ctx,
            "domain": [("location_id.usage", "in", ["internal", "transit"])],
            "views": [(view_id, "list")],
            "help": """
                <p class="o_view_nocontent_smiling_face">
                    {}
                </p>
                <p>
                    {} <span class="fa-solid fa-cog"/>
                </p>
                """.format(
                escape(_("Your stock is currently empty")),
                escape(
                    _(
                        'Press the "New" button to define the quantity for a product in your stock or import quantities from a spreadsheet via the Actions menu'
                    )
                ),
            ),
        }

    def action_apply_inventory(self, date=None):
        ctx = dict(self.env.context or {})
        ctx["default_quant_ids"] = self.ids
        quants_outdated = self.filtered(lambda quant: quant.is_outdated)
        if quants_outdated:
            dbg.logic.debug(
                "action_apply_inventory: outdated %s, opening conflict wizard",
                dbg.rec(quants_outdated),
            )
            ctx["default_quant_to_fix_ids"] = quants_outdated.ids
            return {
                "name": _("Conflict in Inventory Adjustment"),
                "type": "ir.actions.act_window",
                "view_mode": "form",
                "views": [(False, "form")],
                "res_model": "stock.inventory.conflict",
                "target": "new",
                "context": ctx,
            }
        self._apply_inventory(date)
        return None

    def action_stock_quant_relocate(self):
        if (
            len(self.company_id) > 1
            or any(not q.company_id.id for q in self)
            or any(q.product_uom_id.compare(q.quantity, 0) <= 0 for q in self)
        ):
            raise UserError(
                _(
                    "You can only move positive quantities stored in locations used by a single company per relocation."
                )
            )
        context = {
            "default_quant_ids": self.ids,
            "default_lot_id": self.env.context.get("default_lot_id", False),
            "single_product": self.env.context.get("single_product", False),
        }
        return {
            "res_model": "stock.quant.relocate",
            "views": [[False, "form"]],
            "target": "new",
            "type": "ir.actions.act_window",
            "context": context,
        }

    def action_inventory_history(self):
        self.check_singleton()
        action = {
            "name": _("History"),
            "view_mode": "list,form",
            "res_model": "stock.move.line",
            "views": [
                (self.env.ref("stock.view_stock_move_line_list").id, "list"),
                (False, "form"),
            ],
            "type": "ir.actions.act_window",
            "context": {
                "search_default_inventory": 1,
                "search_default_done": 1,
                "search_default_product_id": self.product_id.id,
            },
            "domain": [
                ("company_id", "=", self.company_id.id),
                "|",
                ("location_id", "=", self.location_id.id),
                ("location_dest_id", "=", self.location_id.id),
            ],
        }
        if self.lot_id:
            action["context"]["search_default_lot_id"] = self.lot_id.id
        if self.package_id:
            action["context"]["search_default_package_id"] = self.package_id.id
            action["context"]["search_default_result_package_id"] = self.package_id.id
        if self.owner_id:
            action["context"]["search_default_owner_id"] = self.owner_id.id
        return action

    def action_set_inventory_quantity(self):
        quants_already_set = self.filtered(lambda quant: quant.inventory_quantity_set)
        if quants_already_set:
            dbg.logic.debug(
                "action_set_inventory_quantity: already set %s",
                dbg.rec(quants_already_set),
            )
            ctx = dict(self.env.context or {}, default_quant_ids=self.ids)
            view = self.env.ref("stock.inventory_warning_set_view", False)
            return {
                "name": _("Quantities Already Set"),
                "type": "ir.actions.act_window",
                "view_mode": "form",
                "views": [(view.id, "form")],
                "view_id": view.id,
                "res_model": "stock.inventory.warning",
                "target": "new",
                "context": ctx,
            }
        if not self.env.context.get("from_request_count"):
            for quant in self:
                quant.inventory_quantity = quant.quantity
        self.user_id = self.env.user.id
        self.inventory_quantity_set = True
        return None

    def action_apply_all(self):
        active_domain = self.env.context.get("active_domain") or [
            ("id", "in", self.ids)
        ]
        quant_ids = self.env["stock.quant"].search(active_domain).ids
        ctx = dict(self.env.context or {}, default_quant_ids=quant_ids)
        view = self.env.ref("stock.stock_inventory_adjustment_name_form_view", False)
        return {
            "name": _("Inventory Adjustment"),
            "type": "ir.actions.act_window",
            "views": [(view.id, "form")],
            "res_model": "stock.inventory.adjustment.name",
            "target": "new",
            "context": ctx,
        }

    def action_reset(self):
        ctx = dict(self.env.context or {}, default_quant_ids=self.ids)
        view = self.env.ref("stock.inventory_warning_reset_view", False)
        return {
            "name": _("Quantities To Reset"),
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "views": [(view.id, "form")],
            "view_id": view.id,
            "res_model": "stock.inventory.warning",
            "target": "new",
            "context": ctx,
        }

    def action_clear_inventory_quantity(self):
        self.inventory_quantity = 0
        self.inventory_diff_quantity = 0
        self.inventory_quantity_set = False
        self.user_id = False

    def action_set_inventory_quantity_zero(self):
        self.inventory_quantity = 0
        if self.env.context.get("inventory_report_mode"):
            self._apply_inventory()
        else:
            self.user_id = self.env.user.id

    @api.model
    def _is_inventory_mode(self):
        return self.env.context.get("inventory_mode") and self.env.user.has_group(
            "stock.group_stock_user"
        )

    def _is_outdated(self):
        self.check_singleton()
        return bool(
            self.inventory_quantity_set
            and self.product_id
            and self.product_uom_id.compare(
                self.inventory_quantity - self.inventory_diff_quantity, self.quantity
            )
        )

    @dbg.timed
    def _apply_inventory(self, date=None):
        dbg.pipeline.debug("_apply_inventory start on %s date=%s", dbg.rec(self), date)
        if self.env.context.get("from_inverse_qty") and not any(
            quant.product_uom_id.compare(quant.inventory_diff_quantity, 0)
            for quant in self
        ):
            dbg.logic.debug("_apply_inventory: no diff from inverse, skipped")
            return
        self.inventory_quantity_set = True
        move_vals = []
        default_loss_locations = {}
        loss_location_by_product_company = {
            (quant.product_id.id, quant.company_id.id): quant.product_id.with_company(
                quant.company_id
            ).property_stock_inventory
            for quant in self
        }
        quants_with_missing_loss_locations = self.filtered(
            lambda quant: (
                not loss_location_by_product_company[
                    quant.product_id.id, quant.company_id.id
                ]
            )
        )
        if quants_with_missing_loss_locations:
            dbg.logic.debug(
                "_apply_inventory: %s lack a product loss location, using company default",
                dbg.rec(quants_with_missing_loss_locations),
            )
            for company in quants_with_missing_loss_locations.mapped("company_id"):
                loss_location_id = (
                    self.env["ir.default"]
                    .with_company(company)
                    ._get_model_defaults("product.template")
                    .get("property_stock_inventory")
                )
                default_loss_locations[company.id] = self.env["stock.location"].browse(
                    loss_location_id
                )
        for quant in self:
            if (
                quant.env.context.get("from_inverse_qty")
                and quant.product_uom_id.compare(quant.inventory_diff_quantity, 0) == 0
            ):
                continue
            inventory_location = loss_location_by_product_company[
                quant.product_id.id, quant.company_id.id
            ] or default_loss_locations.get(quant.company_id.id)
            if not inventory_location:
                raise UserError(
                    _(
                        "No inventory loss location is configured for product "
                        "%(product)s (company %(company)s). Set one on the product "
                        "or in the company's default product settings.",
                        product=quant.product_id.display_name,
                        company=quant.company_id.display_name
                        or self.env.company.display_name,
                    )
                )
            applied = quant.inventory_diff_quantity
            intended = quant.inventory_quantity - quant.quantity
            if not math.isclose(
                quant.quantity + applied, quant.inventory_quantity, rel_tol=1e-12
            ):
                dbg.logic.debug(
                    "[quant:%s] _apply_inventory: counted %s against %s, moving %s "
                    "not %s -- will land on %s",
                    quant.id,
                    quant.inventory_quantity,
                    quant.quantity,
                    applied,
                    intended,
                    quant.quantity + applied,
                )
            if quant.product_uom_id.compare(quant.inventory_diff_quantity, 0) > 0:
                move_vals.append(
                    quant._prepare_inventory_move_vals(
                        quant.inventory_diff_quantity,
                        inventory_location,
                        quant.location_id,
                        package_dest_id=quant.package_id,
                    )
                )
            else:
                move_vals.append(
                    quant._prepare_inventory_move_vals(
                        -quant.inventory_diff_quantity,
                        quant.location_id,
                        inventory_location,
                        package_id=quant.package_id,
                    )
                )
        dbg.pipeline.debug(
            "_apply_inventory -> %d inventory moves for %s",
            len(move_vals),
            dbg.rec(self),
        )
        moves = (
            self.env["stock.move"].with_context(inventory_mode=False).create(move_vals)
        )
        moves.with_context(ignore_dest_packages=True)._action_done()
        if date:
            moves.date = date
        moves._trigger_assign()
        self.location_id.sudo().write({"last_inventory_date": fields.Date.today()})
        self._update_next_inventory_date()
        self.action_clear_inventory_quantity()

    def _update_next_inventory_date(self):
        date_by_location = {
            loc: loc._get_next_inventory_date() for loc in self.location_id
        }
        for quant in self:
            quant.inventory_date = date_by_location[quant.location_id]

    @api.model
    def _get_inventory_fields_create(self):
        return ["product_id", "owner_id"] + self._get_inventory_fields_countable()

    @api.model
    def _get_inventory_fields_countable(self):
        return [
            "inventory_quantity",
            "inventory_quantity_auto_apply",
            "inventory_diff_quantity",
            "inventory_date",
            "user_id",
            "inventory_quantity_set",
            "lot_id",
            "location_id",
            "package_id",
        ]

    @api.model
    def _get_forbidden_fields_write(self):
        return ["product_id", "location_id", "lot_id", "package_id", "owner_id"]

    def _prepare_inventory_move_vals(
        self,
        qty,
        location_id,
        location_dest_id,
        package_id=False,
        package_dest_id=False,
    ):
        self.check_singleton()

        res = {
            "product_id": self.product_id.id,
            "product_uom_id": self.product_uom_id.id,
            "product_uom_qty": qty,
            "company_id": self.company_id.id or self.env.company.id,
            "state": "confirmed",
            "location_id": location_id.id,
            "location_dest_id": location_dest_id.id,
            "restrict_partner_id": self.owner_id.id,
            "is_inventory": True,
            "picked": True,
            "move_line_ids": [
                (
                    0,
                    0,
                    {
                        "product_id": self.product_id.id,
                        "product_uom_id": self.product_uom_id.id,
                        "quantity": qty,
                        "location_id": location_id.id,
                        "location_dest_id": location_dest_id.id,
                        "company_id": self.company_id.id or self.env.company.id,
                        "lot_id": self.lot_id.id,
                        "package_id": package_id.id if package_id else False,
                        "result_package_id": (
                            package_dest_id.id if package_dest_id else False
                        ),
                        "owner_id": self.owner_id.id,
                    },
                )
            ],
        }
        if self.env.context.get("inventory_name"):
            res["inventory_name"] = self.env.context.get("inventory_name")

        return res

    def _get_move_line_match_key(self):
        self.check_singleton()
        return (
            self.location_id.id,
            self.package_id.id,
            self.product_id.id,
            self.lot_id.id,
            self.owner_id.id,
        )

    def _read_move_line_dates(self, is_inventory):
        if not self:
            return {}
        package_values = [*self.package_id.ids, False]
        groups = self.env["stock.move.line"]._read_group(
            [
                ("state", "=", "done"),
                ("is_inventory", "=", is_inventory),
                ("product_id", "in", self.product_id.ids),
                ("lot_id", "in", [*self.lot_id.ids, False]),
                ("owner_id", "in", [*self.owner_id.ids, False]),
                "|",
                ("location_id", "in", self.location_id.ids),
                ("location_dest_id", "in", self.location_id.ids),
                "|",
                ("package_id", "in", package_values),
                ("result_package_id", "in", package_values),
            ],
            [
                "product_id",
                "lot_id",
                "package_id",
                "owner_id",
                "result_package_id",
                "location_id",
                "location_dest_id",
            ],
            ["date:max"],
        )

        date_by_quant = {}
        for (
            product,
            lot,
            package,
            owner,
            result_package,
            location,
            location_dest,
            move_line_date,
        ) in groups:
            for loc, pkg in ((location, package), (location_dest, result_package)):
                key = (loc.id, pkg.id, product.id, lot.id, owner.id)
                current = date_by_quant.get(key)
                if not current or move_line_date > current:
                    date_by_quant[key] = move_line_date
        return date_by_quant

    def _create_inventory_quant(self, vals, allowed_fields):
        if any(
            not field.startswith("x_") and field not in allowed_fields for field in vals
        ):
            raise UserError(
                _("Quant's creation is restricted, you can't do this operation.")
            )
        if "inventory_quantity_auto_apply" in vals:
            auto_apply = True
            inventory_quantity = vals.pop("inventory_quantity_auto_apply") or 0
            vals.pop("inventory_quantity", None)
        else:
            auto_apply = False
            inventory_quantity = vals.pop("inventory_quantity", False) or 0
        product = self.env["product.product"].browse(vals["product_id"])
        location = self.env["stock.location"].browse(vals["location_id"])
        lot_id = self.env["stock.lot"].browse(vals.get("lot_id"))
        package_id = self.env["stock.package"].browse(vals.get("package_id"))
        owner_id = self.env["res.partner"].browse(vals.get("owner_id"))
        quant = self.env["stock.quant"]
        if not self.env.context.get("import_file"):
            quant = self.search(
                self._get_domain_gather(
                    product,
                    location,
                    lot_id,
                    package_id,
                    owner_id,
                    strict=True,
                ),
                order="id",
            )
        if lot_id:
            if self.env.context.get("import_file") and lot_id.product_id != product:
                lot_name = lot_id.name
                lot_id = self.env["stock.lot"].search(
                    [("product_id", "=", product.id), ("name", "=", lot_name)],
                    limit=1,
                )
                if not lot_id:
                    company_id = location.company_id or self.env.company
                    lot_id = self.env["stock.lot"].create(
                        {
                            "name": lot_name,
                            "product_id": product.id,
                            "company_id": company_id.id,
                        }
                    )
                vals["lot_id"] = lot_id.id
            quant = quant.filtered(lambda q: q.lot_id)
        created = False
        if quant:
            if len(quant) > 1:
                dbg.logic.debug(
                    "_create_inventory_quant: %d quants match product %s at %s, using %s",
                    len(quant),
                    product.id,
                    location.id,
                    quant[0].id,
                )
            quant = quant[0].sudo()
        else:
            quant = self.sudo().create(vals)
            created = True
        if auto_apply:
            quant.write({"inventory_quantity_auto_apply": inventory_quantity})
        else:
            quant.inventory_quantity = inventory_quantity
            quant.user_id = vals.get("user_id", self.env.user.id)
            quant.inventory_date = fields.Date.today()
        return quant, created

    def move_quants(
        self,
        location_dest_id=False,
        package_dest_id=False,
        message=False,
        unpack=False,
        up_to_parent_packages=False,
    ):
        def update_ancestor_package_dests(quant_ids, package, limit_ids):
            seen = set()
            while package.parent_package_id and not (
                limit_ids and package.id in limit_ids
            ):
                if package.id in seen:
                    return
                seen.add(package.id)
                parent = package.parent_package_id
                if not set(parent.contained_quant_ids.ids) <= quant_ids:
                    return
                package.package_dest_id = parent
                package = parent

        message = message or INVENTORY_REFERENCE_RELOCATED
        move_vals = []
        limit_ids = set(up_to_parent_packages.ids if up_to_parent_packages else [])
        quant_ids = set(self.ids)
        for quant in self:
            result_package_id = package_dest_id
            if not unpack and not package_dest_id:
                result_package_id = quant.package_id
                update_ancestor_package_dests(quant_ids, result_package_id, limit_ids)
            move_vals.append(
                quant.with_context(inventory_name=message)._prepare_inventory_move_vals(
                    quant.quantity,
                    quant.location_id,
                    location_dest_id or quant.location_id,
                    quant.package_id,
                    result_package_id,
                )
            )
        dbg.pipeline.debug(
            "move_quants %s -> location %s package %s unpack=%s: %d moves",
            dbg.rec(self),
            getattr(location_dest_id, "id", location_dest_id),
            getattr(package_dest_id, "id", package_dest_id),
            unpack,
            len(move_vals),
        )
        moves = (
            self.env["stock.move"].with_context(inventory_mode=False).create(move_vals)
        )
        moves.with_context(ignore_dest_packages=True)._action_done()

    def get_aggregate_barcodes(self):
        agg_barcode_max_length = int(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("stock.agg_barcode_max_length", 400)
        )
        barcode_separator = (
            self.env["ir.config_parameter"].sudo().get_param("stock.barcode_separator")
        )
        if not barcode_separator:
            return []

        eol_char = "\t"
        aggregate_barcodes = []
        aggregate_barcode = ""

        uom_unit_id = self.env.ref("uom.product_uom_unit").id
        gs1_quantity_rules = self.env["barcode.rule"].search(
            [
                ("associated_uom_id", "!=", False),
                ("associated_uom_id", "!=", uom_unit_id),
                ("is_gs1_nomenclature", "=", True),
            ]
        )
        gs1_quantity_rules_ai_by_uom = {}

        for rule in gs1_quantity_rules:
            decimal = str(
                len(f"{rule.associated_uom_id.rounding:.10f}".rstrip("0").split(".")[1])
            )
            rule_ai = rule.pattern[1:4] + decimal
            gs1_quantity_rules_ai_by_uom[rule.associated_uom_id.id] = rule_ai

        previous_product = self.env["product.product"]
        for quant in self:
            if not quant.product_id.barcode:
                continue
            barcode = ""
            if previous_product != quant.product_id:
                previous_product = quant.product_id
                if not quant.product_id.valid_ean:
                    barcode += quant.product_id.barcode
            quant_gs1_barcode = quant._get_gs1_barcode(gs1_quantity_rules_ai_by_uom)
            if quant_gs1_barcode:
                barcode += (barcode_separator if barcode else "") + quant_gs1_barcode
            elif quant.tracking == "serial":
                barcode += (barcode_separator if barcode else "") + quant.lot_id.name
            if (
                aggregate_barcode
                and len(aggregate_barcode + barcode) > agg_barcode_max_length
            ):
                aggregate_barcodes.append(aggregate_barcode + eol_char)
                aggregate_barcode = ""
            if barcode:
                if aggregate_barcode and not aggregate_barcode.endswith(
                    barcode_separator
                ):
                    aggregate_barcode += barcode_separator
                aggregate_barcode += barcode

        if aggregate_barcode:
            aggregate_barcodes.append(aggregate_barcode + eol_char)

        return aggregate_barcodes

    def _get_gs1_barcode(self, gs1_quantity_rules_ai_by_uom=False):
        self.check_singleton()
        gs1_quantity_rules_ai_by_uom = gs1_quantity_rules_ai_by_uom or {}
        barcode = ""

        if self.product_id.valid_ean:
            barcode = self.product_id.barcode
            barcode = "01" + "0" * (14 - len(barcode)) + barcode
        elif self.tracking == "none" or not self.lot_id:
            return ""

        if (
            self.tracking != "serial"
            or self.product_uom_id.compare(self.quantity, 1) > 0
        ):
            quantity_ai = gs1_quantity_rules_ai_by_uom.get(self.product_uom_id.id)
            if quantity_ai:
                qty_str = str(round(self.quantity / self.product_uom_id.rounding))
                if len(qty_str) <= 6:
                    barcode += quantity_ai + "0" * (6 - len(qty_str)) + qty_str
            else:
                qty_str = str(round(self.quantity))
                if len(qty_str) <= 8:
                    barcode += "30" + "0" * (8 - len(qty_str)) + qty_str

        if self.lot_id:
            if len(self.lot_id.name) > 20:
                return ""
            tracking_ai = "21" if self.tracking == "serial" else "10"
            barcode += tracking_ai + self.lot_id.name
        return barcode

    def _with_view_context(self):
        if not self.env.user.has_group("stock.group_stock_multi_locations"):
            company_user = self.env.company
            warehouse = self.env["stock.warehouse"].search(
                [("company_id", "=", company_user.id)], limit=1
            )
            if warehouse:
                self = self.with_context(
                    default_location_id=warehouse.lot_stock_id.id,
                    hide_location=not self.env.context.get("always_show_loc", False),
                )

        if self.env.user.has_group("stock.group_stock_user"):
            self = self.with_context(inventory_mode=True)
        return self

    @api.model
    def _prepare_action_quants(self, extend=False):
        if (
            not self.env["ir.config_parameter"]
            .sudo()
            .get_param("stock.skip_quant_tasks")
        ):
            self._run_maintenance_tasks()
        ctx = dict(self.env.context or {})
        ctx["inventory_report_mode"] = True
        ctx.pop("group_by", None)

        action = self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
            "stock.stock_quant_action"
        )
        existing_domain = action.get("domain")
        if isinstance(existing_domain, str):
            existing_domain = literal_eval(existing_domain or "[]")
        action["domain"] = Domain(existing_domain or Domain.TRUE) & Domain(
            "product_id.company_id",
            "in",
            ctx.get("allowed_company_ids", []) + [False],
        )

        form_view = self.env.ref("stock.view_stock_quant_form_editable").id
        if self.env.context.get("inventory_mode") and self.env.user.has_group(
            "stock.group_stock_manager"
        ):
            action["view_id"] = self.env.ref("stock.view_stock_quant_list_editable").id
        else:
            action["view_id"] = self.env.ref("stock.view_stock_quant_list").id
        action.update(
            {
                "views": [
                    (action["view_id"], "list"),
                    (form_view, "form"),
                ],
                "context": ctx,
            }
        )
        if extend:
            action.update(
                {
                    "view_mode": "list,form,pivot,graph",
                    "views": [
                        (action["view_id"], "list"),
                        (form_view, "form"),
                        (self.env.ref("stock.view_stock_quant_pivot").id, "pivot"),
                        (self.env.ref("stock.stock_quant_view_graph").id, "graph"),
                    ],
                }
            )
        action["path"] = "stock-locations"
        return action
