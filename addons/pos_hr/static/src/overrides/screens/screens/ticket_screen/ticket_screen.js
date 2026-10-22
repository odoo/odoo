import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { patch } from "@web/core/utils/patch";

patch(TicketScreen.prototype, {
    getCashier(order) {
        return order.employee_id ? order.employee_id.name : super.getCashier(order);
    },
});
