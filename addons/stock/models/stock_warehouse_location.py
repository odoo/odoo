import logging

from odoo import api, models
from odoo.exceptions import UserError
from odoo.tools import ormcache
from odoo.tools.translate import _

from ..tools import debug_log as dbg
from .stock_warehouse import PARTNER_LOCATION_MISSING, PARTNER_LOCATION_XML_IDS

_logger = logging.getLogger(__name__)


class StockWarehouseLocation(models.Model):
    _inherit = "stock.warehouse"

    @ormcache()
    def _get_sub_location_field_names(self):
        return tuple(self._prepare_sub_location_vals({}))

    def _get_fields_location_step(self):
        return ["reception_steps", "delivery_steps", "company_id"]

    def _get_location_step_values(self, vals, code=False):
        field_names = self._get_fields_location_step()
        values = {name: vals[name] for name in field_names if name in vals}
        missing = [name for name in field_names if name not in values]
        record = self if len(self) == 1 else self.browse()
        if missing:
            defaults = {} if record else self.default_get(missing)
            for name in missing:
                if not record:
                    values[name] = defaults.get(name, False)
                    continue
                value = record[name]
                values[name] = (
                    value.id if isinstance(value, models.BaseModel) else value
                )
        values["code"] = self._normalize_code(
            vals.get("code") or code or (record.code if record else "")
        )
        return values

    def _prepare_sub_location_vals(self, vals, code=False):
        def_values = self._get_location_step_values(vals, code)
        reception_steps = def_values["reception_steps"]
        delivery_steps = def_values["delivery_steps"]
        code = def_values["code"]
        return {
            "lot_stock_id": {
                "name": _("Stock"),
                "active": True,
                "usage": "internal",
                "replenish_location": True,
                "barcode": code + "STOCK",
            },
            "wh_input_stock_loc_id": {
                "name": _("Input"),
                "active": reception_steps != "one_step",
                "usage": "internal",
                "barcode": code + "INPUT",
            },
            "wh_qc_stock_loc_id": {
                "name": _("Quality Control"),
                "active": reception_steps == "three_steps",
                "usage": "internal",
                "barcode": code + "QUALITY",
            },
            "wh_output_stock_loc_id": {
                "name": _("Output"),
                "active": delivery_steps != "ship_only",
                "usage": "internal",
                "barcode": code + "OUTPUT",
            },
            "wh_pack_stock_loc_id": {
                "name": _("Packing Zone"),
                "active": delivery_steps == "pick_pack_ship",
                "usage": "internal",
                "barcode": code + "PACKING",
            },
        }

    @api.model
    def _remove_taken_barcodes(
        self, model_name, values_list, company_id, ignore_ids=()
    ):
        wanted = {values["barcode"] for values in values_list if values.get("barcode")}
        if not wanted:
            return
        domain = [("barcode", "in", list(wanted)), ("company_id", "=", company_id)]
        if ignore_ids:
            domain.append(("id", "not in", list(ignore_ids)))
        taken = {
            record.barcode: record.display_name
            for record in self.env[model_name]
            .with_context(active_test=False)
            .search(domain)
        }
        claimed = set()
        for values in values_list:
            barcode = values.get("barcode")
            if not barcode:
                continue
            owner = taken.get(barcode) or (barcode in claimed and "another of its own")
            if owner:
                _logger.warning(
                    "Barcode %s is already used by %s %s; the warehouse record "
                    "will be left without a barcode.",
                    barcode,
                    self.env[model_name]._description,
                    owner,
                )
                values["barcode"] = False
                continue
            claimed.add(barcode)

    def _create_missing_locations(self, vals):
        location_fields = self._get_sub_location_field_names()
        for warehouse in self:
            if all(warehouse[field] or field in vals for field in location_fields):
                continue
            company_id = vals.get("company_id", warehouse.company_id.id)
            sub_locations = warehouse._prepare_sub_location_vals(
                dict(vals, company_id=company_id), warehouse.code
            )
            missing = {
                field: values
                for field, values in sub_locations.items()
                if not warehouse[field] and field not in vals
            }
            if not missing:
                continue
            dbg.lifecycle.debug(
                "[warehouse:%s] _create_missing_locations: %s",
                warehouse.id,
                list(missing),
            )
            for values in missing.values():
                values["location_id"] = vals.get(
                    "view_location_id", warehouse.view_location_id.id
                )
                values["company_id"] = company_id
            warehouse._remove_taken_barcodes(
                "stock.location", list(missing.values()), company_id
            )
            locations = self.env["stock.location"].create(list(missing.values()))
            # The outer write has not assigned its own picking types yet: the refresh
            # this nested write triggers must not create a second one for them.
            pending = [
                fname
                for fname in vals
                if fname in warehouse._fields
                and warehouse._fields[fname].type == "many2one"
                and warehouse._fields[fname].comodel_name == "stock.picking.type"
            ]
            dbg.logic.debug(
                "[warehouse:%s] _create_missing_locations: picking types pending in the outer write: %s",
                warehouse.id,
                pending,
            )
            warehouse.with_context(stock_pending_picking_type_fields=pending).write(
                dict(zip(missing, locations.ids, strict=True))
            )

    def _update_location_barcodes(self, new_code):
        for warehouse in self:
            values = warehouse._prepare_sub_location_vals({}, new_code)
            locations = self.env["stock.location"].browse()
            wanted = []
            for field_name, location_values in values.items():
                location = warehouse[field_name]
                if not location or not location_values.get("barcode"):
                    continue
                locations |= location
                wanted.append((location, {"barcode": location_values["barcode"]}))
            if not wanted:
                continue
            warehouse._remove_taken_barcodes(
                "stock.location",
                [values for _location, values in wanted],
                warehouse.company_id.id,
                ignore_ids=locations.ids,
            )
            dbg.lifecycle.debug(
                "[warehouse:%s] _update_location_barcodes(%s) on %s",
                warehouse.id,
                new_code,
                dbg.rec(locations),
            )
            for location, location_values in wanted:
                location.barcode = location_values["barcode"]

    def _update_location_reception(self, new_reception_step):
        dbg.lifecycle.debug(
            "_update_location_reception on %s -> %s", dbg.rec(self), new_reception_step
        )
        self.mapped("wh_qc_stock_loc_id").write(
            {"active": new_reception_step == "three_steps"}
        )
        self.mapped("wh_input_stock_loc_id").write(
            {"active": new_reception_step != "one_step"}
        )

    def _update_location_delivery(self, new_delivery_step):
        dbg.lifecycle.debug(
            "_update_location_delivery on %s -> %s", dbg.rec(self), new_delivery_step
        )
        self.mapped("wh_pack_stock_loc_id").write(
            {"active": new_delivery_step == "pick_pack_ship"}
        )
        self.mapped("wh_output_stock_loc_id").write(
            {"active": new_delivery_step != "ship_only"}
        )

    def _get_input_output_locations(self):
        return (
            (
                self.lot_stock_id
                if self.reception_steps == "one_step"
                else self.wh_input_stock_loc_id
            ),
            (
                self.lot_stock_id
                if self.delivery_steps == "ship_only"
                else self.wh_output_stock_loc_id
            ),
        )

    def _get_transit_locations(self):
        return (
            self.company_id.internal_transit_location_id,
            self.env.ref("stock.stock_location_inter_company", raise_if_not_found=False)
            or self.env["stock.location"],
        )

    @api.model
    def _get_partner_location(self, usage):
        location = self.env.ref(
            PARTNER_LOCATION_XML_IDS[usage], raise_if_not_found=False
        )
        if not location:
            location = self.env["stock.location"].search(
                [
                    ("usage", "=", usage),
                    ("company_id", "in", [False, self.env.company.id]),
                ],
                order="company_id, id",
                limit=1,
            )
        if location:
            return location
        raise UserError(
            self.env._(PARTNER_LOCATION_MISSING[usage])  # pylint: disable=gettext-variable
        )

    @api.model
    def _get_partner_locations(self):
        return (
            self._get_partner_location("customer"),
            self._get_partner_location("supplier"),
        )

    def _get_production_location(self):
        location = self.env["stock.location"].search(
            [("usage", "=", "production"), ("company_id", "=", self.company_id.id)],
            limit=1,
        )
        if not location:
            raise UserError(_("Can't find any production location."))
        return location

    @api.model
    def _update_partner_transit_locations(self, partner_id, company_id):
        if not partner_id:
            return
        company = (
            self.env["res.company"].browse(company_id)
            if company_id
            else self.env.company
        )
        transit_location = company.internal_transit_location_id
        if not transit_location:
            return
        dbg.logic.debug(
            "_update_partner_transit_locations: partner %s company %s -> transit %s",
            partner_id,
            company.id,
            transit_location.id,
        )
        self.env["res.partner"].browse(partner_id).with_company(
            company
        )._update_stock_property_locations(transit_location)

    @api.model
    def _is_location_inside(self, location, ancestor):
        root, path = ancestor.parent_path, location.parent_path
        if root and path:
            return path.startswith(root)
        current = location
        seen = set()
        while current and current.id not in seen:
            if current == ancestor:
                return True
            seen.add(current.id)
            current = current.location_id
        return False
