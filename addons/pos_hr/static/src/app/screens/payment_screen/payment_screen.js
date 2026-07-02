import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";

patch(PaymentScreen.prototype, {
    showPaymentMethod(paymentMethod) {
        if (
            this.pos.hasEmployeeRole(["restrictive"]) &&
            (paymentMethod.type === "pay_later" || paymentMethod.glory_websocket_address)
        ) {
            return false;
        }
        return super.showPaymentMethod(paymentMethod);
    },
});
