from odoo import api, models


class ReportMrpReport_Bom_Structure(models.AbstractModel):
    _inherit = "report.mrp.report_bom_structure"

    @api.model
    def _is_buy_route(self, rules, product, bom):
        return super()._is_buy_route(rules, product, bom) and (
            not bom or bom.type != "subcontract"
        )

    @api.model
    def _get_resupply_availability(self, route_info, components):
        resupply_state, resupply_delay = super()._get_resupply_availability(
            route_info, components
        )
        if route_info.get("route_type") == "subcontract" and resupply_delay:
            extra_delay = route_info[
                "bom"
            ].company_id.purchase_config_id.days_to_purchase
            route_info["lead_time"] += extra_delay
            route_info["manufacture_delay"] += extra_delay
            subcontract_delay = resupply_delay + extra_delay
            return ("estimated", subcontract_delay)
        return (resupply_state, resupply_delay)
