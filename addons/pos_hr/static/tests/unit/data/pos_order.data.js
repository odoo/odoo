import { patch } from "@web/core/utils/patch";
import { PosOrder } from "@point_of_sale/app/models/pos_order";

patch(PosOrder.prototype, {
    _load_pos_data_fields() {
        return [...super._load_pos_data_fields(), "employee_id"];
    },
});
