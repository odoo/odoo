import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";

patch(TicketScreen.prototype, {
    async onDoRefund() {
        await super.onDoRefund(...arguments);
        const order = this.getSelectedOrder();
        const discountLines = order.discountLines;
        const destinationOrder = this.pos.getOrder();

        if (discountLines?.length && destinationOrder) {
            const percentage = order.globalDiscountPc;
            this.pos.applyDiscount(percentage, destinationOrder);
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
