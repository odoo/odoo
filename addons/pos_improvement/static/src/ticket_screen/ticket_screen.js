import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { patch } from "@web/core/utils/patch";

patch(TicketScreen.prototype, {
    async doPayment(order) {
        await this._setOrder(order);
        this.pos.pay();
    },
});
