import { patch } from "@web/core/utils/patch";
import { PaymentScreenPaymentLines } from "@point_of_sale/app/screens/payment_screen/payment_lines/payment_lines";

patch(PaymentScreenPaymentLines.prototype, {
    getLineControls(line) {
        const controls = super.getLineControls(line);
        // You can't cancel a payment if it's paid online payment line.
        if (line.online_account_payment_id) {
            controls.end = controls.end.filter((control) => control.id !== "delete");
        }
        return controls;
    },
});
