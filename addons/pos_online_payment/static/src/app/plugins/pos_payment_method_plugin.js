import { patch } from "@web/core/utils/patch";
import { PosPaymentMethodPlugin } from "@point_of_sale/app/plugins/pos_payment_method_plugin";

patch(PosPaymentMethodPlugin.prototype, {
    getPaymentMethods(order) {
        const paymentMethods = super.getPaymentMethods(...arguments);
        // don't allow to update and edit and pay with online payments
        if (order.state === "paid") {
            return paymentMethods.filter((pm) => pm.type !== "online");
        }
        return paymentMethods;
    },
});
