import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreen.prototype, {
    async sendForceDone(line) {
        const paymentInterface = line.payment_method_id.payment_interface;
        if (paymentInterface && line.payment_method_id.payment_provider === "cashdro") {
            paymentInterface.cashdroService
                .cancelPayment(paymentInterface.operationId)
                .catch((error) =>
                    console.warn(`Cashdro cancellation failed after Force Done: ${error}`)
                );
        }
        return super.sendForceDone(...arguments);
    },
});
