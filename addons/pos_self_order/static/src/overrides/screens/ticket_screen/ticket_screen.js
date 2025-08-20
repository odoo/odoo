import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { patch } from "@web/core/utils/patch";

patch(TicketScreen.prototype, {
    getFilteredOrderList() {
        const orders = super.getFilteredOrderList();
        orders.forEach((order) => {
            if (
                (order.pos_reference.includes("Self-Order") ||
                    order.pos_reference.includes("Kiosk")) &&
                !order.online_payment_method_id &&
                !Object.keys(order.last_order_preparation_change.lines).length
            ) {
                order.updateLastOrderChange();
            }
        });
        return orders;
    },
});
