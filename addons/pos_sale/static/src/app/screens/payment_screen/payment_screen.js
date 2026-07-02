import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";

patch(PaymentScreen.prototype, {
    get allowedPaymentMethodIds() {
        const allowedPMIds = super.allowedPaymentMethodIds;
        const settleSoPaymentMethod = this.pos.config.sale_order_payment_method_id;
        if (settleSoPaymentMethod) {
            allowedPMIds.push(settleSoPaymentMethod.id);
        }
        return allowedPMIds;
    },
    updateSelectedPaymentline() {
        if (this.selectedPaymentLine?.payment_method_id?.use_sale_order_payment) {
            return;
        }
        super.updateSelectedPaymentline(...arguments);
    },
});
