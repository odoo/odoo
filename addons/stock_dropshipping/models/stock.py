from odoo import api, fields, models
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog

from ._constants import DROPSHIP_DEST_LOCATION_XMLID, DROPSHIP_SOURCE_LOCATION_XMLID

_debug = DebugLog(__name__)


class StockRule(models.Model):
    _inherit = "stock.rule"

    @api.model
    def _get_procurements_to_merge_groupby(self, procurement):
        return procurement.values.get(
            "sale_line_id"
        ), super()._get_procurements_to_merge_groupby(procurement)

    def _get_partner_id(self, values, rule):
        _debug.logic("dropship_partner_resolve", rules=self)
        route_id = self.env["ir.model.data"]._xmlid_to_res_id(
            "stock_dropshipping.route_drop_shipping"
        )
        if route_id and rule.route_id.id == route_id:
            return False
        return super()._get_partner_id(values, rule)

    def _get_domain_picking_type_code(self):
        codes = super()._get_domain_picking_type_code()
        if self.action == "buy":
            codes = [*codes, "dropship"]
        return codes

    @api.model
    def _get_domain_rule_scope(self, values):
        domain = super()._get_domain_rule_scope(values)
        if "sale_line_id" in values and values.get("company_id"):
            domain &= Domain("company_id", "=", values["company_id"].id)
        return domain


class StockPicking(models.Model):
    _inherit = "stock.picking"

    is_dropship = fields.Boolean(
        string="Is a Dropship",
        compute="_compute_is_dropship",
    )

    @api.depends(
        "location_dest_id.usage",
        "location_dest_id.company_id",
        "location_id.usage",
        "location_id.company_id",
    )
    def _compute_is_dropship(self):
        _debug.perf.count("dropship_flag_compute", pickings=self)
        for picking in self:
            source, dest = picking.location_id, picking.location_dest_id
            picking.is_dropship = (
                source.usage == "supplier"
                or (source.usage == "transit" and not source.company_id)
            ) and (
                dest.usage == "customer"
                or (dest.usage == "transit" and not dest.company_id)
            )

    def _is_to_external_location(self):
        _debug.logic("dropship_external_location_check", pickings=self)
        self.check_singleton()
        return super()._is_to_external_location() or self.is_dropship


class StockPickingType(models.Model):
    _inherit = "stock.picking.type"

    code = fields.Selection(
        selection_add=[("dropship", "Dropship")],
        ondelete={
            "dropship": lambda recs: recs.write({"code": "outgoing", "active": False})
        },
    )

    def _is_default_location_suitable(self, location, partner_usage):
        if self.code == "dropship":
            return location.usage == partner_usage
        return super()._is_default_location_suitable(location, partner_usage)

    def _compute_default_location_src_id(self):
        dropship_types = self.filtered(lambda pt: pt.code == "dropship")
        suppliers = self.env.ref(DROPSHIP_SOURCE_LOCATION_XMLID)
        dropship_types._update_derived_default_location(
            "default_location_src_id", lambda picking_type: suppliers, "supplier"
        )

        super(
            StockPickingType, self - dropship_types
        )._compute_default_location_src_id()

    def _compute_default_location_dest_id(self):
        dropship_types = self.filtered(lambda pt: pt.code == "dropship")
        customers = self.env.ref(DROPSHIP_DEST_LOCATION_XMLID)
        dropship_types._update_derived_default_location(
            "default_location_dest_id", lambda picking_type: customers, "customer"
        )

        super(
            StockPickingType, self - dropship_types
        )._compute_default_location_dest_id()

    @api.depends("default_location_src_id", "default_location_dest_id")
    def _compute_warehouse_id(self):
        super()._compute_warehouse_id()
        for picking_type in self:
            if picking_type.code == "dropship":
                picking_type.warehouse_id = False

    @api.model
    def _get_transfer_codes(self):
        return super()._get_transfer_codes() | {"dropship"}


class StockLot(models.Model):
    _inherit = "stock.lot"

    def _get_partners_from_deliveries(self, pickings):
        partners = self.env["res.partner"]
        for picking in pickings:
            partners |= (
                picking.sale_id.partner_shipping_id
                if picking.is_dropship
                else picking.partner_id
            )
        return partners

    def _get_domain_outgoing_move_lines(self):
        return super()._get_domain_outgoing_move_lines() | Domain(
            [
                ("location_dest_id.usage", "=", "customer"),
                ("location_id.usage", "=", "supplier"),
            ]
        )
