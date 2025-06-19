import { patch } from "@web/core/utils/patch";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";

patch(TicketScreen.prototype, {
    async onDoRefund() {
        await super.onDoRefund(...arguments);
        const order = this.getSelectedOrder();
        const discountLine = order.getDiscountLine();
        const destinationOrder = this.pos.getOrder();

        if (discountLine && destinationOrder && !destinationOrder.getDiscountLine()) {
            const globalDiscount = -discountLine.price_subtotal_incl;
            this.pos.models["pos.order.line"].create({
                qty: 1,
                price_unit:
                    (globalDiscount * destinationOrder.taxTotals.total_amount) /
                        (order.amount_total + globalDiscount) || 1,
                product_id: this.pos.config.discount_product_id,
                order_id: destinationOrder,
            });
        }
    },

    getNumpadClasses() {
        let classes = super.getNumpadClasses();
        // disable numpad for refund discount line
        if (this.isOrderSynced && this.getSelectedOrderlineId()) {
            if (
                this.getSelectedOrder().lines.find(
                    (line) =>
                        line.id == this.getSelectedOrderlineId() &&
                        line.product_id.id === this.pos.config.discount_product_id?.id
                )
            ) {
                classes += " pe-none";
            }
        }
        return classes;
    },
});
