from collections import defaultdict

from odoo import _, api, fields, models
from odoo.tools import OrderedSet


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    mrp_production_count = fields.Integer(
        string="Count of MO Source",
        compute="_compute_mrp_production_count",
        groups="mrp.group_mrp_user",
    )

    @api.depends(
        "line_ids.move_dest_ids.raw_material_production_id",
        "line_ids.move_ids.move_dest_ids.raw_material_production_id",
    )
    def _compute_mrp_production_count(self):
        for purchase in self:
            purchase.mrp_production_count = len(purchase._get_mrp_productions())

    def _get_mrp_productions(self, **kwargs):
        return (
            self.line_ids.move_dest_ids | self.line_ids.move_ids.move_dest_ids
        ).raw_material_production_id

    def action_view_mrp_productions(self):
        self.check_singleton()
        mrp_production_ids = self._get_mrp_productions().ids
        action = {
            "res_model": "mrp.production",
            "type": "ir.actions.act_window",
        }
        if len(mrp_production_ids) == 1:
            action.update(
                {
                    "view_mode": "form",
                    "res_id": mrp_production_ids[0],
                }
            )
        else:
            action.update(
                {
                    "name": _("Manufacturing Source of %s", self.name),
                    "domain": [("id", "in", mrp_production_ids)],
                    "view_mode": "list,form",
                }
            )
        return action


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    def _get_kit_bom_per_line(self):
        product_by_company = defaultdict(OrderedSet)
        for line in self:
            product_by_company[line.company_id].add(line.product_id.id)
        kits_by_company = {
            company: self.env["mrp.bom"]._get_bom_by_product(
                self.env["product.product"].browse(product_ids),
                company_id=company.id,
                bom_type="phantom",
            )
            for company, product_ids in product_by_company.items()
        }
        return {
            line: kit_bom
            for line in self
            if (kit_bom := kits_by_company[line.company_id].get(line.product_id))
        }

    def _get_kit_transferred_qty(self, kit_bom):
        self.check_singleton()
        moves = self._get_kit_moves().filtered(
            lambda m: m.state == "done" and m.location_dest_usage != "inventory"
        )
        order_qty = self.product_uom_id._get_quantity_reconcile(
            self.product_qty, kit_bom.product_uom_id
        )
        filters = {
            "incoming_moves": lambda m: (
                m._is_incoming()
                and (
                    not m.origin_returned_move_id
                    or (m.origin_returned_move_id and m.to_refund)
                )
            ),
            "outgoing_moves": lambda m: m._is_outgoing() and m.to_refund,
        }
        return moves._get_kit_quantity(self.product_id, order_qty, kit_bom, filters)

    def _get_kit_moves(self):
        self.check_singleton()
        accrual_date = self.env.context.get("accrual_entry_date")
        if not accrual_date:
            return self.move_ids
        accrual_date = fields.Date.from_string(accrual_date)
        return self.move_ids.filtered(
            lambda move: fields.Date.context_today(move, move.date) <= accrual_date
        )

    def _get_kit_lines_transferred_qty(self):
        from_stock = self.filtered(
            lambda l: l.qty_transferred_method == "stock_move" and l.state != "cancel"
        )
        from_stock.fetch(["move_ids"])
        lines_stock = from_stock.filtered("move_ids")
        return {
            line: line._get_kit_transferred_qty(kit_bom)
            for line, kit_bom in lines_stock._get_kit_bom_per_line().items()
        }

    def _compute_qty_transferred(self):
        kit_qties = self._get_kit_lines_transferred_qty()
        for line, qty in kit_qties.items():
            line.qty_transferred = qty
        non_kit_lines = self - self.browse([line.id for line in kit_qties])
        super(PurchaseOrderLine, non_kit_lines)._compute_qty_transferred()

    def _prepare_qty_transferred(self):
        kit_qties = self._get_kit_lines_transferred_qty()
        non_kit_lines = self - self.browse([line.id for line in kit_qties])
        transferred_qties = super(
            PurchaseOrderLine, non_kit_lines
        )._prepare_qty_transferred()
        transferred_qties.update(kit_qties)
        return transferred_qties

    def _prepare_stock_move_vals_list(self, picking):
        res = super()._prepare_stock_move_vals_list(picking)
        if len(self.order_id.reference_ids.move_ids.production_group_id) == 1:
            for re in res:
                re["production_group_id"] = (
                    self.order_id.reference_ids.move_ids.production_group_id.id
                )
        sale_line_product = self._get_sale_order_line_product()
        if sale_line_product:
            bom = self.env["mrp.bom"]._get_bom_by_product(
                self.env["product.product"].browse(sale_line_product.id),
                company_id=picking.company_id.id,
                bom_type="phantom",
            )
            bom_kit = bom.get(sale_line_product)
            if bom_kit:
                _dummy, bom_sub_lines = bom_kit._explode(
                    sale_line_product, self.sale_line_id.product_uom_qty
                )
                bom_kit_component = {
                    line["product_id"].id: line.id for line, _ in bom_sub_lines
                }
                for vals in res:
                    if vals["product_id"] in bom_kit_component:
                        vals["bom_line_id"] = bom_kit_component[vals["product_id"]]
        return res

    def _get_upstream_documents_and_responsibles(self, visited):
        return [(self.order_id, self.order_id.user_id, visited)]

    def _get_procurement_qty(self, previous_product_qty=False):
        self.check_singleton()
        if (
            "previous_product_qty" in self.env.context
            and (
                self.env["mrp.bom"]
                .sudo()
                ._get_bom_by_product(
                    self.product_id, bom_type="phantom", company_id=self.company_id.id
                )[self.product_id]
            )
        ):
            return self.env.context["previous_product_qty"].get(self.id, 0.0)
        return super()._get_procurement_qty(previous_product_qty=previous_product_qty)

    def _get_stock_move_dests_initial_demand(self, move_dests):
        kit_bom = self.env["mrp.bom"]._get_bom_by_product(
            self.product_id, bom_type="phantom", company_id=self.company_id.id
        )[self.product_id]
        if kit_bom:
            filters = {
                "incoming_moves": lambda m: True,
                "outgoing_moves": lambda m: False,
            }
            return move_dests._get_kit_quantity(
                self.product_id, self.product_qty, kit_bom, filters
            )
        return super()._get_stock_move_dests_initial_demand(move_dests)

    def _get_sale_order_line_product(self):
        return False
