import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    setSalesPerson(sales_person) {
        this.update({ sales_person_id: sales_person })
    },
})
