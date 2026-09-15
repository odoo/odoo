import { patch } from "@web/core/utils/patch";
import { PaymentScreenPaymentLines } from "@point_of_sale/app/screens/payment_screen/payment_lines/payment_lines";

patch(PaymentScreenPaymentLines.prototype, {
    async sendPaymentAdjust(line) {
        const prevAmount = line.getAmount();
        const amountDiff = line.pos_order_id.getTotalWithTax() - line.pos_order_id.getTotalPaid();
        const newAmount = prevAmount + amountDiff;

        line.setAmount(newAmount);
        line.setPaymentStatus("waiting");
        const isAdjustSuccessful = await line.payment_method_id.payment_terminal?.sendPaymentAdjust(
            line.uuid
        );
        if (!isAdjustSuccessful) {
            line.setAmount(prevAmount);
        }

        line.setPaymentStatus("done");
    },
});
