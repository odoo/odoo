import { patch } from "@web/core/utils/patch";
import { PosOrderLine } from "@point_of_sale/../tests/unit/data/pos_order_line.data";

patch(PosOrderLine.prototype, {
    _load_pos_data_fields() {
        const pos_data_field = super._load_pos_data_fields();
        return [...pos_data_field, "pack_lot_ids"];
    },
});
