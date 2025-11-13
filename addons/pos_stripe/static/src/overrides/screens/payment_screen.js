import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreen.prototype, {
    async addNewPaymentLine(paymentMethod) {
        if (paymentMethod.use_payment_terminal === "stripe" && this.isRefundOrder) {
            const refundedOrder = this.currentOrder.lines[0]?.refunded_orderline_id?.order_id;
            const amountDue = Math.abs(this.currentOrder.getDue());
            const matchedPaymentLine = refundedOrder?.payment_ids.find(
                (line) =>
                    line.payment_method_id.use_payment_terminal === "stripe" &&
                    line.amount >= amountDue
            );
            if (matchedPaymentLine) {
                const paymentLineAddedSuccessfully = await super.addNewPaymentLine(paymentMethod);
                if (paymentLineAddedSuccessfully) {
                    const newPaymentLine = this.paymentLines.at(-1);
                    newPaymentLine.updateRefundPaymentLine(matchedPaymentLine);
                }
                return paymentLineAddedSuccessfully;
            }
        }

        return await super.addNewPaymentLine(paymentMethod);
    },
});
