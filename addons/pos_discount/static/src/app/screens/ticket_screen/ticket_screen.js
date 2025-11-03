import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";

patch(TicketScreen.prototype, {
    async onDoRefund() {
        await super.onDoRefund(...arguments);
        const order = this.getSelectedOrder();
        const discountLine = order.getDiscountLine();
        const destinationOrder = this.pos.getOrder();

        if (discountLine && destinationOrder && !destinationOrder.getDiscountLine()) {
            const globalDiscount = -discountLine.priceIncl;
            const priceUnit =
                (globalDiscount * destinationOrder.prices.taxDetails.total_amount) /
                    (order.amount_total + globalDiscount) || 1;

            this.pos.models["pos.order.line"].create({
                qty: 1,
                price_unit: destinationOrder.orderSign * priceUnit,
                product_id: this.pos.config.discount_product_id,
                order_id: destinationOrder,
            });
        }
    },

    _onUpdateSelectedOrderline() {
        const selectedOrderlineId = this.getSelectedOrderlineId();
        const orderline = this.getSelectedOrder().lines.find(
            (line) => line.id == selectedOrderlineId
        );
        if (orderline && orderline.product_id.id === this.pos.config.discount_product_id?.id) {
            return this.dialog.add(AlertDialog, {
                title: _t("Error"),
                body: _t("You cannot edit a discount line."),
            });
        }
        return super._onUpdateSelectedOrderline(...arguments);
    },
});
