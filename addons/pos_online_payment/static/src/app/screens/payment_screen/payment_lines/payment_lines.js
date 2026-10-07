import { patch } from "@web/core/utils/patch";
import { PaymentScreenPaymentLines } from "@point_of_sale/app/screens/payment_screen/payment_lines/payment_lines";

patch(PaymentScreenPaymentLines.prototype, {
    canDeleteLine(line) {
        // You can't cancel a payment if it's paid online payment line.
        return super.canDeleteLine(...arguments) && !line.online_account_payment_id;
    },
});
