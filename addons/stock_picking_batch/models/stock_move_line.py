from collections import defaultdict

from odoo import _, fields, models
from odoo.fields import Command, Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools.misc import OrderedSet

_debug = DebugLog(__name__)


class WaveFill:
    __slots__ = (
        "line_ids",
        "move_ids",
        "new_move_ids",
        "new_picking_ids",
        "picking_ids",
        "wave",
        "weight",
    )

    def __init__(self, wave):
        self.wave = wave
        self.move_ids = set(wave.move_line_ids.move_id.ids)
        self.picking_ids = set(wave.move_line_ids.picking_id.ids)
        self.new_move_ids = set()
        self.new_picking_ids = set()
        self.weight = 0.0
        self.line_ids = OrderedSet()

    def accept(self, line):
        move_id, picking_id = line.move_id.id, line.picking_id.id
        adds_a_move = move_id not in self.move_ids and move_id not in self.new_move_ids
        adds_a_picking = (
            picking_id not in self.picking_ids
            and picking_id not in self.new_picking_ids
        )
        line_weight = line.product_id.weight * line.quantity_product_uom
        if not self.wave._is_auto_mergeable(
            moves=len(self.new_move_ids) + 1 if adds_a_move else 0,
            pickings=len(self.new_picking_ids) + 1 if adds_a_picking else 0,
            weight=self.weight + line_weight,
        ):
            return False
        if adds_a_move:
            self.new_move_ids.add(move_id)
        if adds_a_picking:
            self.new_picking_ids.add(picking_id)
        self.weight += line_weight
        self.line_ids.add(line.id)
        return True


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    batch_id = fields.Many2one(related="picking_id.batch_id")

    def action_view_add_to_wave(self):
        if "active_wave_id" in self.env.context:
            wave = self.env["stock.picking.batch"].browse(
                self.env.context.get("active_wave_id")
            )
            return self._add_to_wave(wave)
        view = self.env.ref("stock_picking_batch.stock_add_to_wave_form")
        return {
            "name": _("Add to Wave"),
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "stock.add.to.wave",
            "views": [(view.id, "form")],
            "view_id": view.id,
            "target": "new",
        }

    def _prepare_wave_picking_vals(self, wave, picking, lines):
        if lines == picking.move_line_ids and lines.move_id == picking.move_ids:
            wave.picking_ids = [Command.link(picking.id)]
            return None

        picking_to_wave_vals = picking.copy_data(
            {
                "move_ids": [],
                "move_line_ids": [],
                "batch_id": wave.id,
                "date_planned": picking.date_planned,
            }
        )[0]
        for move, move_lines in lines.grouped("move_id").items():
            if move_lines == move.move_line_ids:
                picking_to_wave_vals["move_ids"].append(Command.link(move.id))
            else:
                quantity = sum(
                    line.product_uom_id._get_quantity_in_unit(
                        line.quantity, move.product_id.uom_id, rounding_method="HALF-UP"
                    )
                    for line in move_lines
                )
                new_move_vals = move._split(quantity)
                if not new_move_vals:
                    continue
                new_move_vals[0]["move_line_ids"] = [Command.set(move_lines.ids)]
                picking_to_wave_vals["move_ids"].append(
                    Command.create(new_move_vals[0])
                )
            picking_to_wave_vals["move_line_ids"].extend(
                Command.link(line.id) for line in move_lines
            )
        if not picking_to_wave_vals["move_ids"]:
            return None
        return picking_to_wave_vals

    def _get_add_to_wave_action(self, wave, notification_title):
        if self.env.context.get("from_wave_form"):
            return {
                "type": "ir.actions.client",
                "tag": "soft_reload",
            }
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": notification_title,
                "message": "%s",
                "links": [
                    {
                        "label": wave.name,
                        "url": f"/odoo/action-stock_picking_batch.action_picking_tree_wave/{wave.id}",
                    }
                ],
                "sticky": False,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }

    def _add_to_wave(self, wave=False):
        _debug.pipeline("wave_add_enter", lines=self, wave=wave and wave.id)
        if not wave:
            wave = self.env["stock.picking.batch"].create(
                {
                    "is_wave": True,
                    "picking_type_id": self.picking_type_id[:1].id,
                    "user_id": self.env.context.get("active_owner_id"),
                }
            )
            notification_title = _("The following wave transfer has been created")
        else:
            notification_title = _("The following wave transfer has been updated")
        picking_to_wave_vals_list = []
        split_pickings = self.env["stock.picking"]
        for picking, lines in self.grouped("picking_id").items():
            picking_to_wave_vals = self._prepare_wave_picking_vals(wave, picking, lines)
            if picking_to_wave_vals is None:
                continue
            split_pickings |= picking
            picking_to_wave_vals_list.append(picking_to_wave_vals)

        if picking_to_wave_vals_list:
            split_pickings |= split_pickings.create(picking_to_wave_vals_list)
            split_pickings._add_to_wave_post_picking_split_hook()
        if wave.picking_ids and wave.picking_type_id.batch_auto_confirm:
            wave.action_confirm()
        return self._get_add_to_wave_action(wave, notification_title)

    def _is_auto_waveable(self):
        _debug.logic("auto_waveable_check", lines=self)
        self.check_singleton()
        if (  # noqa: SIM103  the condition reads as a checklist; a bare return would not
            not self.picking_id
            or (
                (
                    self.picking_id.state != "assigned"
                    or self.product_uom_id.is_zero(self.quantity)
                )
                and not self.env.context.get("skip_auto_waveable")
            )
            or self.batch_id.is_wave
            or not self.picking_type_id._is_auto_wave_grouped()
            or (
                self.picking_type_id.wave_group_by_category
                and self.product_id.categ_id
                not in self.picking_type_id.wave_category_ids
            )
        ):
            return False
        return True

    def _auto_wave(self):
        _debug.pipeline("auto_wave_enter", lines=self)
        nearest_parent_locations = defaultdict(lambda: self.env["stock.location"])
        batchable_lines = self.browse()
        for line in self:
            if not line._is_auto_waveable():
                continue
            if not line.picking_type_id.wave_group_by_location:
                batchable_lines |= line
                continue
            nearest_parent_location = line.picking_type_id._get_nearest_wave_location(
                line.location_id
            )
            if nearest_parent_location:
                nearest_parent_locations[line] = nearest_parent_location
                batchable_lines |= line

        remaining_lines = batchable_lines._auto_wave_lines_into_existing_waves(
            nearest_parent_locations
        )
        remaining_lines._auto_wave_lines_into_new_waves(nearest_parent_locations)

    def _get_potential_existing_waves(self, picking_type, batches_to_validate_ids):
        _debug.logic("wave_candidates_search", picking_type=picking_type.id)
        domains = [
            Domain("picking_type_id", "=", picking_type.id),
            Domain("company_id", "in", self.company_id.ids),
            Domain("is_wave", "=", True),
        ]
        if picking_type.batch_auto_confirm:
            domains.append(Domain("state", "not in", ["done", "cancel"]))
        else:
            domains.append(Domain("state", "=", "draft"))
        for criterion in picking_type._get_active_wave_criteria().values():
            ids = self.mapped(criterion.line_path).ids
            domain = Domain(criterion.batch_path, "in", ids)
            if criterion.wave_field:
                domain |= Domain(criterion.wave_field, "in", ids)
            domains.append(domain)
        if batches_to_validate_ids:
            domains.append(Domain("id", "not in", batches_to_validate_ids))
        return self.env["stock.picking.batch"].search(Domain.AND(domains))

    def _get_waves_nearest_parent_locations(self, picking_type, potential_waves):
        waves_nearest_parent_locations = defaultdict(lambda: self.env["stock.location"])
        if not picking_type.wave_group_by_location:
            return waves_nearest_parent_locations, potential_waves

        valid_waves = self.env["stock.picking.batch"]
        for wave in potential_waves:
            nearest_parent_location = picking_type._get_nearest_wave_location(
                wave.wave_location_id
            )
            if nearest_parent_location:
                waves_nearest_parent_locations[wave] = nearest_parent_location
                valid_waves |= wave
        return waves_nearest_parent_locations, valid_waves

    def _get_auto_wave_grouping_key(self, picking_type, nearest_parent_location):
        self.check_singleton()
        return (
            self.company_id,
            *(
                self.mapped(criterion.line_path)
                for criterion in picking_type._get_active_wave_criteria().values()
            ),
            nearest_parent_location,
        )

    def _auto_wave_lines_into_existing_waves(self, nearest_parent_locations):
        _debug.pipeline("auto_wave_into_existing", lines=self)
        remaining_lines = self.browse()
        batches_to_validate_ids = self.env.context.get("batches_to_validate", False)
        for picking_type, lines in self.grouped("picking_type_id").items():
            potential_waves = lines._get_potential_existing_waves(
                picking_type, batches_to_validate_ids
            )
            waves_nearest_parent_locations, potential_waves = (
                lines._get_waves_nearest_parent_locations(picking_type, potential_waves)
            )
            fills_by_key = defaultdict(list)
            for wave in potential_waves:
                key = wave._get_auto_wave_grouping_key(
                    picking_type, waves_nearest_parent_locations[wave]
                )
                fills_by_key[key].append(WaveFill(wave))

            for line in lines:
                key = line._get_auto_wave_grouping_key(
                    picking_type, nearest_parent_locations[line]
                )
                if not any(fill.accept(line) for fill in fills_by_key.get(key, ())):
                    remaining_lines |= line
            for fills in fills_by_key.values():
                for fill in fills:
                    if fill.line_ids:
                        self.browse(fill.line_ids)._add_to_wave(fill.wave)
        return remaining_lines

    def _auto_wave_lines_into_new_waves(self, nearest_parent_locations):
        _debug.pipeline("auto_wave_into_new", lines=self)
        for picking_type, lines in self.grouped("picking_type_id").items():
            grouped = lines.grouped(
                lambda line, picking_type=picking_type: (
                    line._get_auto_wave_grouping_key(
                        picking_type, nearest_parent_locations[line]
                    )
                )
            )
            for wave_lines in grouped.values():
                wave_lines._create_new_waves_for_lines(
                    picking_type, nearest_parent_locations
                )

    def _create_new_waves_for_lines(self, picking_type, nearest_parent_locations):
        _debug.lifecycle("wave_create", picking_type=picking_type.id)
        potential_lines = self.sorted(
            key=lambda line: (line.picking_id.id, line.move_id.id)
        )
        while potential_lines:
            wave_lines = potential_lines._select_lines_for_one_wave(picking_type)
            if not wave_lines:
                potential_lines -= potential_lines[:1]
                continue
            first_line = wave_lines[:1]
            new_wave = self.env["stock.picking.batch"].create(
                {
                    "is_wave": True,
                    "picking_type_id": picking_type.id,
                    "description": first_line._get_auto_wave_description(
                        nearest_parent_locations[first_line]
                    ),
                }
            )
            wave_lines._add_to_wave(new_wave)
            potential_lines -= wave_lines

    def _select_lines_for_one_wave(self, picking_type):
        _debug.logic("wave_line_selection", lines=self, picking_type=picking_type.id)
        fill = WaveFill(
            self.env["stock.picking.batch"].new(
                {"is_wave": True, "picking_type_id": picking_type.id}
            )
        )
        for line in self:
            if not fill.accept(line):
                break
        return self.browse(fill.line_ids)

    def _get_auto_wave_description(self, nearest_parent_location=False):
        self.check_singleton()
        picking_type = self.picking_type_id
        description = self.picking_id._get_auto_batch_description()
        description_items = [description] if description else []
        wave_criteria = picking_type._get_active_grouping_criteria(
            picking_type._get_wave_grouping_criteria()
        )
        for criterion in wave_criteria.values():
            value = self.mapped(criterion.line_path)
            if value:
                description_items.append(value[criterion.label_field])
        if picking_type.wave_group_by_location and nearest_parent_location:
            description_items.append(nearest_parent_location.complete_name)

        return ", ".join(description_items)
