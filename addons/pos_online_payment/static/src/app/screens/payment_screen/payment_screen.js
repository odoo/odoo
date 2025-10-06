import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";

patch(PaymentScreen.prototype, {
    get configPaymentMethods() {
        let configMethods = super.configPaymentMethods;
        // don't allow to update and edit and pay with online payments
        if (this.currentOrder.state === "paid") {
            configMethods = configMethods.filter((pm) => !pm.is_online_payment);
        }
        return configMethods;
    },
    updateSelectedPaymentline() {
        if (
            this.selectedPaymentLine?.payment_method_id?.is_online_payment &&
            this.currentOrder.state === "paid"
        ) {
            return;
        }
        super.updateSelectedPaymentline(...arguments);
    },
});
