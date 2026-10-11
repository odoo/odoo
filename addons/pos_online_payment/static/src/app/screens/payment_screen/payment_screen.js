import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";

patch(PaymentScreen.prototype, {
    get configPaymentMethods() {
        let configMethods = super.configPaymentMethods;
        // don't allow to update and edit and pay with online payments
        if (this.currentOrder.state === "paid") {
            configMethods = configMethods.filter((pm) => pm.type !== "online");
        }
        return configMethods;
    },
});
