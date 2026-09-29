import { patch } from "@web/core/utils/patch";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";

patch(TicketScreen.prototype, {
    async onDoRefund() {
        await super.onDoRefund(...arguments);
        const order = this.getSelectedOrder();
        const discountLines = order.discountLines;
        const destinationOrder = this.pos.getOrder();

        if (discountLines?.length && destinationOrder) {
            const { value, type } = order.globalDiscountPc;
            this.pos.applyDiscount(value, type, destinationOrder);
        }
    },

    _onUpdateSelectedOrderline() {
        const selectedOrderlineId = this.getSelectedOrderlineId();
        const orderline = this.getSelectedOrder().lines.find(
            (line) => line.id == selectedOrderlineId
        );
        if (orderline?.isDiscountLine) {
            return this.pos.showDiscountLineEditError();
        }
        return super._onUpdateSelectedOrderline(...arguments);
    },
});
