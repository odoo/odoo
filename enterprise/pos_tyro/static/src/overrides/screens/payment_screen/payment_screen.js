import { patch } from "@web/core/utils/patch";
import { uniqueBy } from "@point_of_sale/app/models/utils/unique_by";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";

patch(PaymentScreen.prototype, {
    get refundLines() {
        const order = this.pos.get_order();
        const orderLinesToRefund = order.lines
            .map((line) => line.refunded_orderline_id)
            .filter((line) => line != null);
        const paymentLinesToRefund = uniqueBy(
            orderLinesToRefund.flatMap((line) => line.order_id?.payment_ids ?? []),
            (line) => line.id
        );
        const amountDue = -order.get_due();
        const validLinesToRefund = paymentLinesToRefund.filter(
            (line) =>
                this.payment_methods_from_config.some(
                    (paymentMethod) => paymentMethod.id === line.payment_method_id.id
                ) && line.amount <= amountDue
        );
        if (
            validLinesToRefund.length < 2 ||
            !validLinesToRefund.some(
                (line) => line.payment_method_id.use_payment_terminal === "tyro"
            )
        ) {
            // This 'refund by payment line' functionality is only needed to meet Tyro's
            // certification criteria regarding split payments/refunds. So for now, we
            // will only show it when refunding a transaction that used Tyro and has
            // multiple payments.
            return [];
        }
        const refundIds = this.paymentLines
            .map((line) => line.refundedPaymentId)
            .filter((id) => id != null);
        return validLinesToRefund.filter((line) => !refundIds.includes(line.id));
    },
    async addPaymentLineFromRefundLine(refundLine) {
        if (await this.addNewPaymentLine(refundLine.payment_method_id)) {
            const newPaymentLine = this.paymentLines.at(-1);
            newPaymentLine.set_amount(-refundLine.amount);
            newPaymentLine.refundedPaymentId = refundLine.id;
        }
    },
});
