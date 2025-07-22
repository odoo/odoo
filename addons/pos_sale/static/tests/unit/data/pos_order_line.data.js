import { patch } from "@web/core/utils/patch";
import { PosOrderLine } from "@point_of_sale/../tests/unit/data/pos_order_line.data";

patch(PosOrderLine.prototype, {
    _load_pos_data_fields() {
        return [
            ...super._load_pos_data_fields(),
            "sale_order_origin_id",
            "sale_order_line_id",
            "down_payment_details",
            "settled_order_id",
            "settled_invoice_id",
        ];
    },
});
