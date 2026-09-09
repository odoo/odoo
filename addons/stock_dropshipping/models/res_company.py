from odoo import api, models
from odoo.libs.debug_log import DebugLog

from ._constants import DROPSHIP_DEST_LOCATION_XMLID, DROPSHIP_SOURCE_LOCATION_XMLID

_debug = DebugLog(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"

    def _create_dropship_sequence(self):
        _debug.lifecycle("dropship_sequence_create", companies=self)
        dropship_vals = [
            {
                "name": "Dropship (%s)" % company.name,
                "code": "stock.dropshipping",
                "company_id": company.id,
                "prefix": "DS/",
                "padding": 5,
            }
            for company in self
        ]
        if dropship_vals:
            self.env["ir.sequence"].create(dropship_vals)

    @api.model
    def create_missing_dropship_sequence(self):
        having = (
            self.env["ir.sequence"]
            .search([("code", "=", "stock.dropshipping")])
            .mapped("company_id")
        )
        self._get_companies_without(having)._create_dropship_sequence()

    def _create_per_company_sequences(self):
        super()._create_per_company_sequences()
        self._create_dropship_sequence()

    def _create_dropship_picking_type(self):
        _debug.lifecycle("dropship_picking_type_create", companies=self)
        dropship_vals = []
        for company in self:
            sequence = self.env["ir.sequence"].search(  # noqa: E8507 - company setup: one lookup per company
                [
                    ("code", "=", "stock.dropshipping"),
                    ("company_id", "=", company.id),
                ]
            )
            dropship_vals.append(
                {
                    "name": "Dropship",
                    "company_id": company.id,
                    "warehouse_id": False,
                    "sequence_id": sequence.id,
                    "code": "dropship",
                    "default_location_src_id": self.env.ref(
                        DROPSHIP_SOURCE_LOCATION_XMLID
                    ).id,
                    "default_location_dest_id": self.env.ref(
                        DROPSHIP_DEST_LOCATION_XMLID
                    ).id,
                    "sequence_code": "DS",
                    "use_existing_lots": False,
                }
            )
        if dropship_vals:
            self.env["stock.picking.type"].create(dropship_vals)

    @api.model
    def create_missing_dropship_picking_type(self):
        having = (
            self.env["stock.picking.type"]
            .search([("code", "=", "dropship")])
            .company_id
        )
        self._get_companies_without(having)._create_dropship_picking_type()

    def _create_per_company_picking_types(self):
        super()._create_per_company_picking_types()
        self._create_dropship_picking_type()

    def _create_dropship_rule(self):
        _debug.lifecycle("dropship_rule_create", companies=self)
        dropship_route = self.env.ref("stock_dropshipping.route_drop_shipping")
        supplier_location = self.env.ref("stock.stock_location_suppliers")
        customer_location = self.env.ref("stock.stock_location_customers")

        dropship_vals = []
        for company in self:
            dropship_picking_type = self.env["stock.picking.type"].search(  # noqa: E8507 - company setup: one lookup per company
                [
                    ("company_id", "=", company.id),
                    ("code", "=", "dropship"),
                ],
                limit=1,
                order="sequence",
            )
            if not dropship_picking_type:
                continue
            dropship_vals.append(
                {
                    "name": "%s → %s"
                    % (supplier_location.name, customer_location.name),
                    "action": "buy",
                    "location_dest_id": customer_location.id,
                    "location_src_id": supplier_location.id,
                    "procure_method": "make_to_stock",
                    "route_id": dropship_route.id,
                    "picking_type_id": dropship_picking_type.id,
                    "company_id": company.id,
                }
            )
        if dropship_vals:
            self.env["stock.rule"].create(dropship_vals)

    @api.model
    def create_missing_dropship_rule(self):
        dropship_route = self.env.ref("stock_dropshipping.route_drop_shipping")
        having = (
            self.env["stock.rule"]
            .search([("route_id", "=", dropship_route.id)])
            .mapped("company_id")
        )
        self._get_companies_without(having)._create_dropship_rule()

    def _create_per_company_rules(self):
        super()._create_per_company_rules()
        self._create_dropship_rule()
