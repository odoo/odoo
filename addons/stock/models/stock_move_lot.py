import logging
from collections import defaultdict
from re import fullmatch as regex_fullmatch

from odoo import api, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command, Domain
from odoo.tools.misc import OrderedSet
from odoo.tools.translate import _

from ..tools import debug_log as dbg
from .stock_move import FIELD_DATA_IGNORED, GENERATED_LOT_VALS_MAX

_logger = logging.getLogger(__name__)


class StockMoveLot(models.Model):
    _inherit = "stock.move"

    @api.depends("move_line_ids.lot_id", "move_line_ids.quantity")
    def _compute_lot_ids(self):
        domain = [
            ("move_id", "in", self.ids),
            ("lot_id", "!=", False),
            ("quantity", "!=", 0.0),
        ]
        lots_by_move_id = self.env["stock.move.line"]._read_group(
            domain,
            ["move_id"],
            ["lot_id:array_agg"],
        )
        lots_by_move_id = {move.id: lot_ids for move, lot_ids in lots_by_move_id}
        for move in self:
            move.lot_ids = lots_by_move_id.get(move._origin.id, [])

    def _inverse_lot_ids(self):
        for move in self:
            if move.product_id.tracking == "none":
                continue
            if (
                move.state == "assigned"
                and all(ml.lot_id in move.lot_ids for ml in move.move_line_ids)
                and move.move_line_ids.lot_id == move.lot_ids
            ):
                dbg.logic.debug(
                    "[move:%s] _inverse_lot_ids: lines already match", move.id
                )
                continue
            move._update_move_lines_for_lots()
        self.env.add_to_compute(self._fields["quantity"], self)

    @api.onchange("lot_ids")
    def _onchange_lot_ids(self):
        product = self.product_id
        if product.tracking == "none":
            return None

        new_lot_names = OrderedSet(lot.name for lot in self.lot_ids if lot.name)
        assigned_quantity, assignable_quantity, nb_of_assignable_sml = (
            self._get_lot_line_quantities(new_lot_names)
        )
        old_lot_names = (
            OrderedSet(lot.name for lot in self._origin.lot_ids if lot.name)
            if self._origin
            else OrderedSet()
        )
        extra_lot_names = new_lot_names - old_lot_names
        quantity = assigned_quantity + assignable_quantity
        if not extra_lot_names:
            self.update({"quantity": quantity})
            return None

        base_location = self.picking_id.location_id or self.location_id
        quant_domain = self._get_domain_extra_lot_quant(extra_lot_names)
        minimal_quantity = product.uom_id._get_quantity_in_unit(1, self.product_uom_id)
        if self._is_reservation_bypass_required():
            nb_of_exceed = max(len(extra_lot_names) - nb_of_assignable_sml, 0)
            if nb_of_exceed > 0:
                quantity = max(
                    self.product_uom_qty,
                    quantity + nb_of_exceed * minimal_quantity,
                )
        else:
            quantity += self._get_extra_lot_reservable_quantity(
                extra_lot_names,
                quant_domain,
                base_location,
                assigned_quantity,
                assignable_quantity,
                minimal_quantity,
            )
        self.update({"quantity": quantity})
        return self._get_misplaced_serial_warning(quant_domain, base_location)

    def _get_lot_line_quantities(self, new_lot_names):
        assigned_quantity = 0
        assignable_quantity = 0
        nb_of_assignable_sml = 0
        for sml in self.move_line_ids:
            sml_quantity = sml.product_uom_id._get_quantity_in_unit(
                sml.quantity,
                self.product_uom_id,
            )
            if not sml.lot_id.name and not sml.lot_name:
                assignable_quantity += sml_quantity
                nb_of_assignable_sml += 1
            elif (sml.lot_id.name or sml.lot_name) in new_lot_names:
                assigned_quantity += sml_quantity
        return assigned_quantity, assignable_quantity, nb_of_assignable_sml

    def _get_domain_extra_lot_quant(self, extra_lot_names):
        extra_lot_ids = {
            rec["id"]
            for rec in self.env["stock.lot"]
            .sudo()
            .search_read(
                [
                    ("product_id", "=", self.product_id.id),
                    ("name", "in", extra_lot_names),
                ],
                ["id"],
            )
        }
        return Domain(
            [
                ("product_id", "=", self.product_id.id),
                ("lot_id", "in", extra_lot_ids),
                ("quantity", "!=", 0),
                ("location_id.usage", "in", ("internal", "transit", "customer")),
                ("company_id", "in", (False, self.company_id.id)),
            ],
        )

    def _get_extra_lot_reservable_quantity(
        self,
        extra_lot_names,
        quant_domain,
        base_location,
        assigned_quantity,
        assignable_quantity,
        minimal_quantity,
    ):
        uom = self.product_uom_id
        available_quantity_by_lot_name = self._get_available_quantity_by_lot_name(
            quant_domain,
            base_location,
        )
        new_assigned_quantity = len(extra_lot_names) * minimal_quantity
        qty_free = self.product_uom_qty - assigned_quantity - new_assigned_quantity
        for lot_name in extra_lot_names:
            if uom.compare(qty_free, 0.0) <= 0:
                continue
            extra_qty = (
                min(
                    available_quantity_by_lot_name[lot_name],
                    qty_free + minimal_quantity,
                )
                - minimal_quantity
            )
            if uom.compare(extra_qty, 0) > 0:
                new_assigned_quantity += extra_qty
                qty_free -= extra_qty
        return max(0, new_assigned_quantity - assignable_quantity)

    def _get_available_quantity_by_lot_name(self, quant_domain, base_location):
        quant_by_lot = (
            self.env["stock.quant"]
            .sudo()
            ._read_group(
                Domain.AND(
                    [quant_domain, Domain("location_id", "child_of", base_location.id)],
                ),
                ["lot_id"],
                ["quantity:sum", "reserved_quantity:sum"],
            )
        )
        available_quantity_by_lot_name = defaultdict(float)
        for lot, total_quantity, reserved_quantity in quant_by_lot:
            available_quantity_by_lot_name[lot.name] += (
                self.product_id.uom_id._get_quantity_in_unit(
                    total_quantity - reserved_quantity,
                    self.product_uom_id,
                )
            )
        return available_quantity_by_lot_name

    def _get_misplaced_serial_warning(self, quant_domain, base_location):
        if self.product_id.tracking != "serial":
            return None
        problematic_quants = (
            self.env["stock.quant"]
            .sudo()
            .search(
                Domain.AND(
                    [
                        quant_domain,
                        ~Domain("location_id", "child_of", base_location.id),
                    ],
                ),
            )
        )
        if not problematic_quants:
            return None
        sn_to_location = "".join(
            _(
                "\n(%(serial_number)s) exists in location %(location)s",
                serial_number=quant.lot_id.display_name,
                location=quant.location_id.display_name,
            )
            for quant in problematic_quants
        )
        return {
            "warning": {
                "title": _("Warning"),
                "message": _(
                    "Unavailable Serial numbers. Please correct the serial numbers encoded: %(serial_numbers_to_locations)s",
                    serial_numbers_to_locations=sn_to_location,
                ),
            },
        }

    @dbg.timed
    @api.model
    def action_generate_lot_line_vals(
        self,
        context_data,
        mode,
        first_lot,
        count,
        lot_text,
    ):
        default_vals = self._prepare_lot_generation_defaults(context_data, mode)
        lot_names, lot_qties = self._prepare_lot_generation_names(
            default_vals, mode, first_lot, count, lot_text
        )
        dbg.logic.debug(
            "action_generate_lot_line_vals mode=%s first=%s count=%s -> %d names",
            mode,
            first_lot,
            count,
            len(lot_names),
        )
        generator = self.with_context(
            exclude_sml_ids=set(context_data.get("exclude_sml_ids") or ()),
            force_lot_m2o=bool(context_data.get("force_lot_m2o")),
        )
        vals_list = generator._prepare_generated_move_line_vals(
            default_vals, lot_names, lot_qties
        )
        product = self.env["product.product"].browse(default_vals["product_id"])
        if default_vals.get("picking_type_id"):
            picking_type = self.env["stock.picking.type"].browse(
                default_vals["picking_type_id"],
            )
            if generator._is_lot_materialization_required(picking_type):
                self._create_lot_ids_from_move_line_vals(
                    vals_list,
                    default_vals["product_id"],
                    default_vals.get("company_id", False),
                )
        self._format_move_line_vals_for_client(vals_list)
        if mode == "generate":
            self._update_lot_sequence(product, first_lot, len(lot_qties))
        return vals_list

    @api.model
    def _prepare_lot_generation_defaults(self, context_data, mode):
        if not context_data.get("default_product_id"):
            raise UserError(_("No product found to generate Serials/Lots for."))
        if mode not in ("generate", "import"):
            raise UserError(_("Invalid mode %s.", mode))

        default_vals = {}
        for key in context_data:
            if key.startswith("default_"):
                default_vals[key.removeprefix("default_")] = context_data[key]

        required_keys = ["tracking", "location_dest_id"]
        if default_vals.get("tracking") == "lot" and mode == "generate":
            required_keys.append("quantity")
        missing = [key for key in required_keys if key not in default_vals]
        if missing:
            raise UserError(
                _(
                    "Missing required values to generate Serials/Lots: %(keys)s.",
                    keys=", ".join(missing),
                ),
            )
        return default_vals

    @api.model
    def _prepare_lot_generation_names(
        self, default_vals, mode, first_lot, count, lot_text
    ):
        if default_vals["tracking"] == "lot" and mode == "generate":
            lot_qties = self._prepare_lot_generation_split(
                default_vals["quantity"], count
            )
        else:
            lot_qties = [1] * self._coerce_generated_lot_count(count)

        if mode == "generate":
            lot_names = [
                {"lot_name": name}
                for name in self.env["stock.lot"].prepare_lot_names(
                    self._coerce_lot_text(
                        first_lot, _("The first Serial/Lot must be text.")
                    ),
                    len(lot_qties),
                )
            ]
        else:
            lot_names = self.split_lots(
                self._coerce_lot_text(
                    lot_text, _("The Serials/Lots to import must be text.")
                ),
            )
            lot_qties = [1] * len(lot_names)
        self._check_generated_lot_count(len(lot_qties))
        return lot_names, lot_qties

    @api.model
    def _coerce_generated_lot_count(self, count):
        not_whole = _("The number of Serials/Lots to generate must be a whole number.")
        try:
            line_count = int(count)
        except TypeError, ValueError:
            raise UserError(not_whole) from None
        if isinstance(count, float) and line_count != count:
            raise UserError(not_whole)
        self._check_generated_lot_count(line_count)
        return max(line_count, 0)

    @api.model
    def _coerce_lot_text(self, value, message):
        if not value:
            return ""
        if not isinstance(value, str):
            raise UserError(message)
        return value

    @api.model
    def _prepare_lot_generation_split(self, quantity, qty_per_lot):
        try:
            quantity = float(quantity)
            qty_per_lot = float(qty_per_lot)
        except TypeError, ValueError:
            raise UserError(
                _("The quantity and the quantity per lot must be numbers."),
            ) from None
        if qty_per_lot <= 0:
            raise UserError(
                _("The quantity per lot should always be a positive value."),
            )
        line_count = int(quantity // qty_per_lot)
        self._check_generated_lot_count(line_count)
        leftover = quantity % qty_per_lot
        qty_array = [qty_per_lot] * line_count
        if leftover:
            qty_array.append(leftover)
        return qty_array

    @api.model
    def _check_generated_lot_count(self, count):
        if count > GENERATED_LOT_VALS_MAX:
            raise UserError(
                _(
                    "You cannot generate more than %s Serials/Lots at once.",
                    GENERATED_LOT_VALS_MAX,
                ),
            )

    @api.model
    def _prepare_generated_move_line_vals(self, default_vals, lot_names, lot_qties):
        loc_dest = self.env["stock.location"].browse(
            default_vals["location_dest_id"],
        )
        product = self.env["product.product"].browse(default_vals["product_id"])
        lots = [
            lot if lot.get("quantity") else {**lot, "quantity": qty}
            for lot, qty in zip(lot_names, lot_qties, strict=True)
        ]
        line_uom = self.env["uom.uom"].browse(
            default_vals.get("uom_id", product.uom_id.id)
        )
        locations = loc_dest._get_putaway_strategy_batch(
            product,
            [
                line_uom._get_quantity_in_unit(
                    lot["quantity"], product.uom_id, rounding_method="HALF-UP"
                )
                for lot in lots
            ],
        )
        return [
            {
                **default_vals,
                **lot,
                "location_dest_id": location.id,
                "product_uom_id": line_uom.id,
            }
            for lot, location in zip(lots, locations, strict=True)
        ]

    @api.model
    def _format_move_line_vals_for_client(self, vals_list):
        MoveLine = self.env["stock.move.line"]
        relational_fields = {
            f_name
            for f_name, field in MoveLine._fields.items()
            if field.type == "many2one"
        }
        ids_by_field = defaultdict(OrderedSet)
        for values in vals_list:
            for f_name in values.keys() & relational_fields:
                if values[f_name]:
                    ids_by_field[f_name].add(values[f_name])
        name_by_field_id = {}
        for f_name, ids in ids_by_field.items():
            for record in MoveLine[f_name].browse(ids):
                name_by_field_id[f_name, record.id] = record.display_name
        for values in vals_list:
            for f_name in values.keys() & relational_fields:
                value = values[f_name]
                values[f_name] = {
                    "id": value,
                    "display_name": name_by_field_id.get((f_name, value), False),
                }

    @api.model
    def _update_lot_sequence(self, product, first_lot, generated_count):
        if not product.lot_sequence_id or not first_lot:
            return
        current_sequence = product.lot_sequence_id._get_current_sequence()
        increment = product.lot_sequence_id.number_increment
        first_number = current_sequence.number_next_actual - increment
        final_number = first_number
        if first_lot == product.lot_sequence_id.get_next_char(first_number):
            final_number = first_number + generated_count
        elif first_lot == product.lot_sequence_id.get_next_char(
            first_number + increment
        ):
            final_number = first_number + increment + generated_count
        final_number = max(final_number, current_sequence.number_next_actual)
        if final_number != current_sequence.number_next_actual:
            dbg.lifecycle.debug(
                "_update_lot_sequence: product %s sequence %s -> %s",
                product.id,
                current_sequence.number_next_actual,
                final_number,
            )
            current_sequence.sudo().write({"number_next_actual": final_number})

    def _add_serial_move_line_to_vals_list(self, reserved_quant, quantity):
        return [
            self._prepare_move_line_vals(quantity=1, reserved_quant=reserved_quant)
            for _i in range(self._get_serial_line_count(quantity))
        ]

    def _get_serial_line_count(self, quantity):
        return max(int(self.product_id.uom_id.round(quantity)), 0)

    def _get_serial_count_to_prefill(self):
        self.check_singleton()
        if self.next_serial_count:
            return 0
        return self._get_serial_line_count(self.product_qty)

    def _update_move_lines_for_lots(self):
        self.check_singleton()
        product = self.product_id
        (
            move_lines_commands,
            available_move_lines,
            assigned_lot_ids,
            free_uom_qty,
        ) = self._classify_move_lines_for_lots()
        is_reservation_bypass_required = self._is_reservation_bypass_required()
        extra_uom_qty = free_uom_qty - len(set(self.lot_ids.ids) - assigned_lot_ids)
        dbg.logic.debug(
            "[move:%s] _update_move_lines_for_lots: lots %s, assigned %s, free lines %s, "
            "free qty %s, bypass=%s",
            self.id,
            self.lot_ids.ids,
            sorted(assigned_lot_ids),
            dbg.rec(available_move_lines),
            free_uom_qty,
            is_reservation_bypass_required,
        )
        quants_by_lot = {}
        if not is_reservation_bypass_required:
            quants_by_lot = (
                self.env["stock.quant"]
                ._gather(product, self.location_id)
                .grouped("lot_id")
            )
        for lot in self.lot_ids:
            if lot.id in assigned_lot_ids:
                continue
            if is_reservation_bypass_required:
                commands, available_move_lines, extra_uom_qty = (
                    self._prepare_lot_commands_bypass(
                        lot, available_move_lines, extra_uom_qty
                    )
                )
            else:
                commands, extra_uom_qty = self._prepare_lot_commands_reserve(
                    lot,
                    quants_by_lot.get(lot, self.env["stock.quant"]),
                    extra_uom_qty,
                )
            move_lines_commands += commands
        if not is_reservation_bypass_required and available_move_lines:
            move_lines_commands += self._prepare_lot_commands_rebalance_unlotted(
                available_move_lines,
                extra_uom_qty,
            )
        dbg.lifecycle.debug(
            "[move:%s] _update_move_lines_for_lots: %d line commands",
            self.id,
            len(move_lines_commands),
        )
        self.write({"move_line_ids": move_lines_commands})

    def _classify_move_lines_for_lots(self):
        self.check_singleton()
        product = self.product_id
        commands = []
        lot_id_by_name = {lot.name: lot.id for lot in self.lot_ids}
        available_move_line_ids = []
        free_uom_qty = self.product_uom_id._get_quantity_in_unit(
            max(self.quantity, self.product_uom_qty),
            product.uom_id,
        )
        assigned_lot_ids = set()
        for ml in self.move_line_ids:
            lot_name = ml.lot_id.name or ml.lot_name
            if ml.product_uom_id.is_zero(ml.quantity):
                continue
            if not ml.lot_id and not ml.lot_name:
                available_move_line_ids.append(ml.id)
            elif lot_name in lot_id_by_name:
                lot_id = lot_id_by_name[lot_name]
                assigned_lot_ids.add(lot_id)
                free_uom_qty -= ml.product_uom_id._get_quantity_in_unit(
                    ml.quantity,
                    product.uom_id,
                )
                commands.append(Command.update(ml.id, {"lot_id": lot_id}))
            else:
                commands.append(Command.delete(ml.id))
        return (
            commands,
            self.env["stock.move.line"].browse(available_move_line_ids),
            assigned_lot_ids,
            free_uom_qty,
        )

    def _create_lot_ids_from_move_line_vals(
        self,
        vals_list,
        product_id,
        company_id=False,
    ):
        lot_names = [vals["lot_name"] for vals in vals_list if vals.get("lot_name")]
        lot_ids = self.env["stock.lot"].search(
            [
                ("product_id", "=", product_id),
                "|",
                ("company_id", "=", company_id),
                ("company_id", "=", False),
                ("name", "in", lot_names),
            ],
        )
        lot_id_names = set(lot_ids.mapped("name"))
        missing_names = dict.fromkeys(
            lot_name for lot_name in lot_names if lot_name not in lot_id_names
        )
        lots_to_create_vals = [
            {"product_id": product_id, "name": lot_name} for lot_name in missing_names
        ]
        dbg.lifecycle.debug(
            "_create_lot_ids_from_move_line_vals: product %s, %d existing, creating %d",
            product_id,
            len(lot_ids),
            len(lots_to_create_vals),
        )
        lot_ids |= self.env["stock.lot"].create(lots_to_create_vals)

        lot_id_by_name = {lot.name: lot.id for lot in lot_ids}
        for vals in vals_list:
            lot_name = vals.get("lot_name", None)
            if not lot_name:
                continue
            vals["lot_id"] = lot_id_by_name[lot_name]
            vals["lot_name"] = False

    def _str_to_field_data(self, string, options):
        string = string.replace(",", ".")
        if regex_fullmatch(r"[0-9]+\.?[0-9]*|\.[0-9]+", string):
            return {"quantity": float(string)}
        return False

    def _update_move_lines_for_serials(
        self,
        next_serial,
        next_serial_count=False,
        location_id=False,
    ):
        self.check_singleton()
        count = next_serial_count or self.next_serial_count
        if not count:
            raise ValidationError(
                _(
                    "The number of Serial Numbers to generate must be greater than zero.",
                ),
            )
        lot_names = self.env["stock.lot"].prepare_lot_names(next_serial, count)
        dbg.logic.debug(
            "[move:%s] _update_move_lines_for_serials from %s x%s -> %s",
            self.id,
            next_serial,
            count,
            lot_names[:8],
        )
        field_data = [{"lot_name": lot_name, "quantity": 1} for lot_name in lot_names]
        if self._is_lot_materialization_required():
            self._create_lot_ids_from_move_line_vals(
                field_data,
                self.product_id.id,
                self.company_id.id,
            )
        move_lines_commands = self._prepare_serial_move_line_commands(
            field_data,
            location_dest_id=location_id,
        )
        self.move_line_ids = move_lines_commands
        return True

    def _prepare_serial_move_line_commands(
        self,
        field_data,
        location_dest_id=False,
        origin_move_line=None,
    ):
        self.check_singleton()
        origin_move_line = origin_move_line or self.env["stock.move.line"]
        loc_dest = origin_move_line.location_dest_id or location_dest_id
        move_line_vals = {
            "picking_id": self.picking_id.id,
            "location_id": self.location_id.id,
            "product_id": self.product_id.id,
            "product_uom_id": self.product_id.uom_id.id,
        }
        move_lines = self.move_line_ids.filtered(
            lambda ml: not ml.lot_id and not ml.lot_name,
        )

        if origin_move_line:
            move_line_vals.update(
                {
                    "owner_id": origin_move_line.owner_id.id,
                    "package_id": origin_move_line.package_id.id,
                },
            )

        reused, created = field_data[: len(move_lines)], field_data[len(move_lines) :]
        move_lines_commands = [
            Command.update(move_lines[i].id, command_vals)
            for i, command_vals in enumerate(reused)
        ]
        already_placed = defaultdict(float)
        for line, command_vals in zip(move_lines, reused, strict=False):
            already_placed[line.location_dest_id.id] += command_vals["quantity"]

        if loc_dest:
            locations = [loc_dest] * len(created)
        else:
            locations = self.location_dest_id._get_putaway_strategy_batch(
                self.product_id,
                [command_vals["quantity"] for command_vals in created],
                additional_qty=already_placed,
            )
        move_lines_commands += [
            Command.create(
                {**move_line_vals, **command_vals, "location_dest_id": location.id},
            )
            for command_vals, location in zip(created, locations, strict=True)
        ]
        return move_lines_commands

    def _get_formatting_options(self, strings):
        return {}

    def _prepare_lot_move_line_vals(self, lot, quantity, reserved_quant=None):
        self.check_singleton()
        vals = self._prepare_move_line_vals(
            quantity=quantity,
            reserved_quant=reserved_quant,
        )
        vals.update({"lot_id": lot.id, "lot_name": lot.name})
        if self.product_id.tracking == "serial":
            vals.update({"quantity": 1.0, "product_uom_id": self.product_id.uom_id.id})
        return vals

    def _prepare_lot_commands_bypass(self, lot, available_move_lines, extra_uom_qty):
        self.check_singleton()
        product = self.product_id
        uom = product.uom_id if product.tracking == "serial" else self.product_uom_id
        if available_move_lines:
            move_line = available_move_lines[0]
            new_vals = {
                "lot_id": lot.id,
                "lot_name": lot.name,
                "product_uom_id": uom.id,
                "quantity": (
                    1.0 if product.tracking == "serial" else move_line.quantity
                ),
            }
            commands = [Command.update(move_line.id, new_vals)]
            available_move_lines -= move_line
            extra_uom_qty -= (
                uom._get_quantity_in_unit(new_vals["quantity"], product.uom_id) - 1
            )
        else:
            quantity_to_reserve = 1.0
            if (
                product.tracking == "lot"
                and product.uom_id.compare(extra_uom_qty, 0.0) > 0
            ):
                quantity_to_reserve += extra_uom_qty
                extra_uom_qty = 0
            commands = [
                Command.create(
                    self._prepare_lot_move_line_vals(lot, quantity_to_reserve),
                ),
            ]
        return commands, available_move_lines, extra_uom_qty

    def _prepare_lot_commands_reserve(self, lot, quants, extra_uom_qty):
        self.check_singleton()
        product = self.product_id
        commands = []
        reserved = False
        for quant in quants:
            if reserved and product.uom_id.compare(extra_uom_qty, 0.0) <= 0:
                break
            if product.uom_id.compare(quant.available_quantity, 0.0) <= 0:
                continue
            quantity_to_reserve = min(
                quant.available_quantity,
                max(extra_uom_qty if reserved else extra_uom_qty + 1, 1),
            )
            if product.uom_id.compare(quantity_to_reserve, 0.0) > 0:
                if product.tracking == "serial":
                    quantity_to_reserve = 1
                commands.append(
                    Command.create(
                        self._prepare_lot_move_line_vals(
                            lot,
                            quantity_to_reserve,
                            reserved_quant=quant,
                        ),
                    ),
                )
                extra_uom_qty -= (
                    quantity_to_reserve if reserved else quantity_to_reserve - 1
                )
                reserved = True
        if not reserved:
            commands.append(
                Command.create(self._prepare_lot_move_line_vals(lot, 1.0)),
            )
        return commands, extra_uom_qty

    def _prepare_lot_commands_rebalance_unlotted(
        self, available_move_lines, extra_uom_qty
    ):
        self.check_singleton()
        product = self.product_id
        commands = [Command.delete(ml.id) for ml in available_move_lines]
        for move_line in available_move_lines:
            if product.uom_id.compare(extra_uom_qty, 0.0) <= 0:
                break
            ml_quantity = move_line.product_uom_id._get_quantity_in_unit(
                move_line.quantity,
                product.uom_id,
            )
            quantity_to_reserve = min(ml_quantity, extra_uom_qty)
            new_ml_quantity = product.uom_id._get_quantity_in_unit(
                quantity_to_reserve,
                move_line.product_uom_id,
            )
            commands.append(
                Command.create(
                    move_line.copy_data(
                        {
                            "quantity": new_ml_quantity,
                            "picked": move_line.picked,
                        },
                    )[0],
                ),
            )
            extra_uom_qty -= quantity_to_reserve
        return commands

    @api.model
    def split_lots(self, lots):
        separation_char = "\t"

        if not lots:
            return []

        split_lines = [line for line in lots.splitlines() if line]
        parts_per_line = [
            line.replace(";", separation_char).split(separation_char)
            for line in split_lines
        ]
        options = self._get_formatting_options(
            [part for parts in parts_per_line for part in parts[1:]],
        )
        move_lines_vals = []
        for lot_text, lot_text_parts in zip(split_lines, parts_per_line, strict=True):
            move_line_vals = {
                "lot_name": lot_text,
                "quantity": 1,
            }
            for extra_string in lot_text_parts[1:]:
                field_data = self._str_to_field_data(extra_string, options)
                if field_data:
                    lot_text = lot_text_parts[0]
                    if field_data == FIELD_DATA_IGNORED:
                        move_line_vals.update(lot_name=lot_text)
                    else:
                        move_line_vals.update(**field_data, lot_name=lot_text)
                else:
                    move_line_vals["lot_name"] = lot_text
                    break
            move_lines_vals.append(move_line_vals)
        dbg.logic.debug(
            "split_lots: %d lines -> %d move line vals",
            len(split_lines),
            len(move_lines_vals),
        )
        return move_lines_vals

    def _is_lot_materialization_required(self, picking_type=None):
        if picking_type is None:
            picking_type = self.picking_type_id
        return picking_type.use_existing_lots

    def _check_quantity(self):
        serial_moves = self.filtered(lambda m: m.product_id.tracking == "serial")
        if not serial_moves:
            return
        dbg.logic.debug("_check_quantity on serial moves %s", dbg.rec(serial_moves))
        (
            self.env["stock.quant"]
            .sudo()
            .search(
                [
                    ("product_id", "in", serial_moves.product_id.ids),
                    ("location_id", "child_of", serial_moves.location_dest_id.ids),
                    ("lot_id", "in", serial_moves.sudo().lot_ids.ids),
                ],
            )
            ._check_quantity()
        )
