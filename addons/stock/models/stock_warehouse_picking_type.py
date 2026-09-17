import logging

from odoo import api, models
from odoo.libs.colors import TAG_COLOR_INDICES
from odoo.tools.translate import _

from ..tools import debug_log as dbg
from .stock_warehouse import WAREHOUSE_PICKING_TYPE_CODES

_logger = logging.getLogger(__name__)


class StockWarehousePickingType(models.Model):
    _inherit = "stock.warehouse"

    @dbg.timed
    def _create_or_update_picking_types(self):
        self.check_singleton()
        PickingType = self.env["stock.picking.type"]

        warehouse_data = {}
        data = self._prepare_picking_type_update_vals()
        create_data = self._prepare_picking_type_create_vals()
        codes = self._get_picking_type_codes()
        suffixes = self._get_picking_type_barcode_suffixes(codes)
        self._check_picking_type_registry(data, create_data, suffixes, codes)
        self._update_picking_type_barcodes(data, suffixes)

        to_update = [field for field in data if self[field]]
        pending = set(self.env.context.get("stock_pending_picking_type_fields", ()))
        to_create = [
            field for field in data if not self[field] and field not in pending
        ]
        if pending:
            dbg.logic.debug(
                "[warehouse:%s] picking types left to the pending outer write: %s",
                self.id,
                sorted(pending),
            )
        dbg.lifecycle.debug(
            "[warehouse:%s] picking types: update %s, create %s",
            self.id,
            to_update,
            to_create,
        )

        for field in to_update:
            self[field].write(data[field])
        if to_update:
            PickingType.browse(
                self[field].id for field in to_update
            )._update_reference_sequences(only={"company_id"})

        if to_create:
            color = self._get_picking_type_color()
            base_sequence = self._get_last_picking_type_sequence()
            picking_type_vals = []
            for offset, field in enumerate(to_create, start=1):
                values = dict(data[field], **create_data[field])
                values.update(
                    warehouse_id=self.id,
                    color=color,
                    sequence_code=codes[field],
                    sequence=base_sequence + offset,
                )
                picking_type_vals.append(values)
            picking_types = PickingType.create(picking_type_vals)
            for field, picking_type in zip(to_create, picking_types, strict=True):
                warehouse_data[field] = picking_type.id

        self._link_return_picking_types(warehouse_data)
        return warehouse_data

    def _link_return_picking_types(self, created_ids):
        PickingType = self.env["stock.picking.type"]
        if not {"in_type_id", "out_type_id"} & set(created_ids):
            return
        in_type = PickingType.browse(created_ids.get("in_type_id")) or self.in_type_id
        out_type = (
            PickingType.browse(created_ids.get("out_type_id")) or self.out_type_id
        )
        if not (in_type and out_type):
            return
        dbg.lifecycle.debug(
            "_link_return_picking_types: in %s <-> out %s", in_type.id, out_type.id
        )
        in_type.return_picking_type_id = out_type
        out_type.return_picking_type_id = in_type

    def _get_picking_type_color(self):
        self.check_singleton()
        PickingType = self.env["stock.picking.type"].with_context(active_test=False)
        own = PickingType.search([("warehouse_id", "=", self.id)], limit=1, order="id")
        if own:
            return own.color
        used = {
            color
            for (color,) in PickingType._read_group(
                [
                    ("warehouse_id", "!=", False),
                    ("company_id", "=", self.company_id.id),
                ],
                ["color"],
            )
        }
        return next((color for color in TAG_COLOR_INDICES if color not in used), 0)

    def _get_last_picking_type_sequence(self):
        [(highest,)] = (
            self.env["stock.picking.type"]
            .with_context(active_test=False)
            ._read_group([], aggregates=["sequence:max"])
        )
        return highest or 0

    @api.model
    def _check_picking_type_registry(self, update_data, create_data, suffixes, codes):
        expected = set(codes)
        declared = [s for s in suffixes.values() if isinstance(s, str)]
        duplicated = sorted({s for s in declared if declared.count(s) > 1})
        if duplicated:
            raise ValueError(
                "stock.warehouse picking-type barcode suffixes are not unique: %s "
                "is claimed by more than one picking type, so their barcodes would "
                "collide. _get_picking_type_barcode_suffixes must return a distinct "
                "suffix per picking type." % duplicated
            )
        for label, mapping in (
            ("_prepare_picking_type_update_vals", update_data),
            ("_prepare_picking_type_create_vals", create_data),
            ("_get_picking_type_barcode_suffixes", suffixes),
        ):
            missing = expected - set(mapping)
            extra = set(mapping) - expected
            if missing or extra:
                raise ValueError(
                    "stock.warehouse picking-type declarations disagree: "
                    "%s is missing %s and declares unregistered %s. Every "
                    "picking type must appear in _get_picking_type_codes, "
                    "_prepare_picking_type_create_vals, "
                    "_prepare_picking_type_update_vals and "
                    "_get_picking_type_barcode_suffixes."
                    % (label, sorted(missing) or "nothing", sorted(extra) or "nothing")
                )

    def _get_picking_type_codes(self):
        return dict(WAREHOUSE_PICKING_TYPE_CODES)

    def _get_picking_type_barcode_suffixes(self, codes=None):
        return dict(codes if codes is not None else self._get_picking_type_codes())

    def _update_picking_type_barcodes(self, update_data, suffixes):
        self.check_singleton()
        code = self._get_normalized_code()
        fields_order = list(suffixes)
        wanted = [{"barcode": code + suffixes[field]} for field in fields_order]
        owned = (
            self.env["stock.picking.type"]
            .with_context(active_test=False)
            .search([("warehouse_id", "=", self.id)])
        )
        self._remove_taken_barcodes(
            "stock.picking.type", wanted, self.company_id.id, ignore_ids=owned.ids
        )
        for field, values in zip(fields_order, wanted, strict=True):
            update_data[field]["barcode"] = values["barcode"]

    def _prepare_picking_type_update_vals(self):
        input_loc, output_loc = self._get_input_output_locations()
        return {
            "in_type_id": {
                "default_location_dest_id": input_loc.id,
            },
            "out_type_id": {
                "default_location_src_id": output_loc.id,
            },
            "pick_type_id": {
                "active": self.delivery_steps != "ship_only" and self.active,
                "default_location_dest_id": (
                    output_loc.id
                    if self.delivery_steps == "pick_ship"
                    else self.wh_pack_stock_loc_id.id
                ),
            },
            "pack_type_id": {
                "active": self.delivery_steps == "pick_pack_ship" and self.active,
                "default_location_dest_id": output_loc.id,
            },
            "qc_type_id": {
                "active": self.reception_steps == "three_steps" and self.active,
            },
            "store_type_id": {
                "active": self.reception_steps != "one_step" and self.active,
                "default_location_src_id": (
                    input_loc.id
                    if self.reception_steps == "two_steps"
                    else self.wh_qc_stock_loc_id.id
                ),
            },
            "int_type_id": {},
            "xdock_type_id": {
                "active": self.reception_steps != "one_step"
                and self.delivery_steps != "ship_only"
                and self.active,
            },
        }

    def _prepare_picking_type_create_vals(self):
        _input_loc, output_loc = self._get_input_output_locations()
        return {
            "in_type_id": {
                "name": _("Receipts"),
                "code": "incoming",
                "use_existing_lots": False,
                "company_id": self.company_id.id,
            },
            "out_type_id": {
                "name": _("Delivery Orders"),
                "code": "outgoing",
                "use_create_lots": False,
                "print_label": True,
                "company_id": self.company_id.id,
            },
            "pack_type_id": {
                "name": _("Pack"),
                "code": "internal",
                "use_create_lots": False,
                "use_existing_lots": True,
                "default_location_src_id": self.wh_pack_stock_loc_id.id,
                "default_location_dest_id": output_loc.id,
                "company_id": self.company_id.id,
            },
            "pick_type_id": {
                "name": _("Pick"),
                "code": "internal",
                "use_create_lots": False,
                "use_existing_lots": True,
                "default_location_src_id": self.lot_stock_id.id,
                "company_id": self.company_id.id,
            },
            "qc_type_id": {
                "name": _("Quality Control"),
                "code": "internal",
                "use_create_lots": False,
                "use_existing_lots": True,
                "default_location_src_id": self.wh_input_stock_loc_id.id,
                "default_location_dest_id": self.wh_qc_stock_loc_id.id,
                "company_id": self.company_id.id,
            },
            "store_type_id": {
                "name": _("Storage"),
                "code": "internal",
                "use_create_lots": False,
                "use_existing_lots": True,
                "default_location_dest_id": self.lot_stock_id.id,
                "company_id": self.company_id.id,
            },
            "int_type_id": {
                "name": _("Internal Transfers"),
                "code": "internal",
                "use_create_lots": False,
                "use_existing_lots": True,
                "default_location_src_id": self.lot_stock_id.id,
                "default_location_dest_id": self.lot_stock_id.id,
                "active": self.env.user.has_group("stock.group_stock_multi_locations"),
                "company_id": self.company_id.id,
            },
            "xdock_type_id": {
                "name": _("Cross Dock"),
                "code": "internal",
                "use_create_lots": False,
                "use_existing_lots": True,
                "default_location_src_id": self.wh_input_stock_loc_id.id,
                "default_location_dest_id": self.wh_output_stock_loc_id.id,
                "company_id": self.company_id.id,
            },
        }
