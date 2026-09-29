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

    // TODO: remove in master (20.0)
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

    onClickOrderline(orderline) {
        if (
            this.getSelectedOrder()?.finalized &&
            this.getSelectedOrderlineId() == orderline.id &&
            orderline.product_id.id === this.pos.config.discount_product_id?.id
        ) {
            {
                return this.pos.showDiscountLineEditError();
            }
        }
        return super.onClickOrderline(...arguments);
    },
});
