import { patch } from "@web/core/utils/patch";
import { PaymentScreenPaymentLines } from "@point_of_sale/app/screens/payment_screen/payment_lines/payment_lines";

patch(PaymentScreenPaymentLines.prototype, {
    async sendPaymentAdjust(line) {
        const prevAmount = line.get_amount();
        const amountDiff =
            line.pos_order_id.get_total_with_tax() - line.pos_order_id.get_total_paid();
        const newAmount = prevAmount + amountDiff;

        line.set_amount(newAmount);
        line.set_payment_status("waiting");

        const isAdjustSuccessful =
            await line.payment_method_id.payment_terminal?.send_payment_adjust(line.uuid);
        if (!isAdjustSuccessful) {
            line.set_amount(prevAmount);
        }

        line.set_payment_status("done");
    },
});
