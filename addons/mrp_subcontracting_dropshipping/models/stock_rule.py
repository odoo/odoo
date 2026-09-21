from odoo import models


class StockRule(models.Model):
    _inherit = "stock.rule"

    def _prepare_purchase_order_vals(self, company_id, origins, values):
        if not values[0].get("partner_id") and (
            company_id.mrp_subcontracting_config_id.subcontracting_location_id.parent_path
            in self.location_dest_id.parent_path
            or self.location_dest_id.is_subcontract()
        ):
            move = values[0].get("move_dest_ids")
            if move and move.raw_material_production_id.subcontractor_id:
                values[0]["partner_id"] = (
                    move.raw_material_production_id.subcontractor_id.id
                )
        return super()._prepare_purchase_order_vals(company_id, origins, values)

    def _get_domain_po(self, company_id, values, partner):
        domain = super()._get_domain_po(company_id, values, partner)
        carries_destination = (
            self.picking_type_id.default_location_dest_id.usage == "customer"
        )
        if values.get("partner_id", False) and carries_destination:
            domain += (("dest_address_id", "=", values.get("partner_id")),)
        return domain
