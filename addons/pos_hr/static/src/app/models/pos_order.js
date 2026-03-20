import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    // @Override
    getCashierName() {
        return this.employee_id?.name?.split(" ").at(0) || super.getCashierName(...arguments);
    },
});
