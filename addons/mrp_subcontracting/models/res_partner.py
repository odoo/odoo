from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    property_stock_subcontractor = fields.Many2one(
        comodel_name="stock.location",
        string="Subcontractor Location",
        company_dependent=True,
        help="The stock location used as source and destination when sending\
        goods to this contact during a subcontracting process.",
    )
    is_subcontractor = fields.Boolean(
        string="Subcontractor",
        compute="_compute_is_subcontractor",
        search="_search_is_subcontractor",
        store=False,
    )
    bom_ids = fields.Many2many(
        comodel_name="mrp.bom",
        string="BoMs for which the Partner is one of the subcontractors",
        compute="_compute_bom_ids",
    )
    production_ids = fields.Many2many(
        comodel_name="mrp.production",
        string="MRP Productions for which the Partner is the subcontractor",
        compute="_compute_production_ids",
    )
    picking_ids = fields.Many2many(
        comodel_name="stock.picking",
        string="Stock Pickings for which the Partner is the subcontractor",
        compute="_compute_picking_ids",
    )

    def _compute_bom_ids(self):
        results = self.env["mrp.bom"]._read_group(
            [
                (
                    "subcontractor_ids.commercial_partner_id",
                    "in",
                    self.commercial_partner_id.ids,
                )
            ],
            ["subcontractor_ids"],
            ["id:array_agg"],
        )
        for partner in self:
            bom_ids = []
            for subcontractor, ids in results:
                if (
                    partner.id == subcontractor.id
                    or subcontractor.id in partner.child_ids.ids
                ):
                    bom_ids += ids
            partner.bom_ids = bom_ids

    def _compute_production_ids(self):
        results = self.env["mrp.production"]._read_group(
            [
                (
                    "subcontractor_id.commercial_partner_id",
                    "in",
                    self.commercial_partner_id.ids,
                )
            ],
            ["subcontractor_id"],
            ["id:array_agg"],
        )
        for partner in self:
            production_ids = []
            for subcontractor, ids in results:
                if (
                    partner.id == subcontractor.id
                    or subcontractor.id in partner.child_ids.ids
                ):
                    production_ids += ids
            partner.production_ids = production_ids

    def _compute_picking_ids(self):
        results = self.env["stock.picking"]._read_group(
            [
                (
                    "partner_id.commercial_partner_id",
                    "in",
                    self.commercial_partner_id.ids,
                )
            ],
            ["partner_id"],
            ["id:array_agg"],
        )
        for partner in self:
            picking_ids = []
            for partner_rg, ids in results:
                if (
                    partner_rg.id == partner.id
                    or partner_rg.id in partner.child_ids.ids
                ):
                    picking_ids += ids
            partner.picking_ids = picking_ids

    def _search_is_subcontractor(self, operator, value):
        if operator != "in":
            return NotImplemented
        subcontractor_ids = (
            self.env["mrp.bom"]
            .search([("type", "=", "subcontract")])
            .subcontractor_ids.ids
        )
        return [("id", "in", subcontractor_ids)]

    def _compute_is_subcontractor(self):
        candidates = self.filtered(
            lambda partner: any(user._is_portal() for user in partner.user_ids)
        )
        subcontractor_ids = set()
        if candidates:
            subcontractor_ids = {
                subcontractor.id
                for [subcontractor] in self.env["mrp.bom"]._read_group(
                    [
                        ("type", "=", "subcontract"),
                        (
                            "subcontractor_ids",
                            "in",
                            (candidates | candidates.commercial_partner_id).ids,
                        ),
                    ],
                    ["subcontractor_ids"],
                )
            }
        for partner in self:
            partner.is_subcontractor = partner in candidates and bool(
                subcontractor_ids & set((partner | partner.commercial_partner_id).ids)
            )
