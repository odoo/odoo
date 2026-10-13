import { patch } from "@web/core/utils/patch";
import { PaymentScreenPaymentLines } from "@point_of_sale/app/screens/payment_screen/payment_lines/payment_lines";

patch(PaymentScreenPaymentLines.prototype, {
    getPaymentActionState(line) {
        if (line.payment_method_id.type === "online" && line.payment_status === "waiting") {
            return null;
        }
        return super.getPaymentActionState(line);
    },
});
