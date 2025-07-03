import { patch } from "@web/core/utils/patch";
import { hootPosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { models } from "@web/../tests/web_test_helpers";

export class SaleOrder extends models.ServerModel {
    _name = "sale.order";

    _load_pos_data_fields() {
        return [
            "name",
            "state",
            "user_id",
            "order_line",
            "partner_id",
            "pricelist_id",
            "fiscal_position_id",
            "amount_total",
            "amount_untaxed",
            "amount_unpaid",
            "picking_ids",
            "partner_shipping_id",
            "partner_invoice_id",
            "date_order",
            "write_date",
        ];
    }
}

patch(hootPosModels, [...hootPosModels, SaleOrder]);
