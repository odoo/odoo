import { patch } from "@web/core/utils/patch";
import { hootPosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { models } from "@web/../tests/web_test_helpers";

export class SaleOrderLine extends models.ServerModel {
    _name = "sale.order.line";

    _load_pos_data_fields() {
        return [
            "discount",
            "display_name",
            "price_total",
            "price_unit",
            "product_id",
            "product_uom_qty",
            "qty_delivered",
            "qty_invoiced",
            "qty_to_invoice",
            "display_type",
            "name",
            "tax_ids",
            "is_downpayment",
            "extra_tax_data",
            "write_date",
            "is_repair_line",
        ];
    }
}

patch(hootPosModels, [...hootPosModels, SaleOrderLine]);
