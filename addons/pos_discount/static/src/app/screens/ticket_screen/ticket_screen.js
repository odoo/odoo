import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";

patch(TicketScreen.prototype, {
    async onDoRefund() {
        await super.onDoRefund(...arguments);
        const order = this.getSelectedOrder();
        const destinationOrder = this.pos.getOrder();
        if (!order?.discountLines?.length || !destinationOrder) {
            return;
        }
        const { value, type } = this.getRefundDiscount(order, destinationOrder);
        if (value) {
            await this.pos.applyDiscount(value, type, destinationOrder);
        }
    },

    getRefundDiscount(order, destinationOrder) {
        const { value, type } = order.globalDiscountPc;
        if (type === "percent") {
            return { value, type };
        }
        const totalIncl = (lines) =>
            lines.reduce((total, line) => total + line.prices.total_included, 0);
        const base = totalIncl(order.lines.filter((line) => line.isGlobalDiscountApplicable()));
        if (!base) {
            return { value: 0, type: "fixed" };
        }
        const refundBase = -totalIncl(
            destinationOrder.lines.filter((line) => line.isGlobalDiscountApplicable())
        );
        const discountAmount = -totalIncl(order.discountLines);
        return {
            value: this.pos.currency.round((discountAmount * refundBase) / base),
            type: "fixed",
        };
    },

    _onUpdateSelectedOrderline() {
        const selectedOrderlineId = this.getSelectedOrderlineId();
        const orderline = this.getSelectedOrder().lines.find(
            (line) => line.id == selectedOrderlineId
        );

        if (orderline && orderline.isDiscountLine) {
            return this.dialog.add(AlertDialog, {
                title: _t("Oh snap !"),
                body: _t("You cannot edit a discount line."),
            });
        }
        return super._onUpdateSelectedOrderline(...arguments);
    },

    onClickOrderline(orderline) {
        if (
            this.getSelectedOrder()?.finalized &&
            this.getSelectedOrderlineId() == orderline.id &&
            orderline.isDiscountLine
        ) {
            {
                return this.dialog.add(AlertDialog, {
                    title: _t("Oh snap !"),
                    body: _t("You cannot edit a discount line."),
                });
            }
        }
        return super.onClickOrderline(...arguments);
    },
});
