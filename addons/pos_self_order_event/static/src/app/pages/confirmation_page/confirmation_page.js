import { ConfirmationPage } from "@pos_self_order/app/pages/confirmation_page/confirmation_page";
import { patch } from "@web/core/utils/patch";

patch(ConfirmationPage.prototype, {
    hasEventTicket(order) {
        if (!order) {
            return false;
        }
        return order.lines?.some((line) => line.event_ticket_id);
    },
});
