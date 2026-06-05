import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreen.prototype, {
    async sendForceDone(line) {
        const paymentInterface = line.payment_method_id.payment_terminal;
        if (paymentInterface && line.payment_method_id.payment_method_type === "cashdro") {
            paymentInterface.cashdroService.cancelPayment(paymentInterface.operationId);
        }
        return super.sendForceDone(...arguments);
    },
});
