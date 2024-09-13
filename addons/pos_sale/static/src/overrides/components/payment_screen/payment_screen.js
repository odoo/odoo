import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";

patch(PaymentScreen.prototype, {
    async validateOrder(isForceValidate) {
        this.currentOrder.set_to_invoice(this.currentOrder.is_to_invoice());
        return await super.validateOrder(isForceValidate);
    },
});
