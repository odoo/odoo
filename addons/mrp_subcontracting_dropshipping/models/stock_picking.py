from odoo import models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _compute_is_dropship(self):
        dropship_subcontract_pickings = self.filtered(
            lambda p: (
                p.location_dest_id.is_subcontract()
                and p.location_id.usage == "supplier"
            )
        )
        dropship_subcontract_pickings.is_dropship = True
        super(StockPicking, self - dropship_subcontract_pickings)._compute_is_dropship()

    def _get_warehouse(self, subcontract_move):
        if subcontract_move.sale_line_id:
            return subcontract_move.sale_line_id.order_id.warehouse_id
        return super()._get_warehouse(subcontract_move)

    def _prepare_subcontract_mo_vals(self, subcontract_move, bom, references):
        res = super()._prepare_subcontract_mo_vals(subcontract_move, bom, references)
        if not res.get("picking_type_id") and (
            subcontract_move.location_dest_id.usage == "customer"
            or subcontract_move.location_dest_id.is_subcontract()
        ):
            default_warehouse = self.env["stock.warehouse"].search(
                [("company_id", "=", subcontract_move.company_id.id)], limit=1
            )
            res["picking_type_id"] = default_warehouse.subcontracting_type_id.id
        return res
