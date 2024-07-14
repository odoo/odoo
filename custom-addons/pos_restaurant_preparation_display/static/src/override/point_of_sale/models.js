/** @odoo-module **/
import { Order } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";
import "@pos_preparation_display/override/point_of_sale/models";

patch(Order.prototype, {
    // Override
    preparePreparationOrder(order, orderline) {
        const preparationOrder = super.preparePreparationOrder(...arguments);
        preparationOrder.pos_table_id = order.tableId;

        return preparationOrder;
    },
});
