import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    // Override
    preparePreparationOrder(order, orderline) {
        const preparationOrder = super.preparePreparationOrder(...arguments);
        preparationOrder.pos_table_id = order.tableId;

        return preparationOrder;
    },
});
