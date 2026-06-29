import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    setSalesPerson(salesperson) {
        this.update({ salesperson_id: salesperson });
    },

    getSalesPerson() {
        return this.salesperson_id;
    },
});
