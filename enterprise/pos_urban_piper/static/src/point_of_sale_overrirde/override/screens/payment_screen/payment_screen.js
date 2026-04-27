import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";

patch(PaymentScreen.prototype, {
    /**
     * @override
     */
    setup() {
        super.setup();
        if (this.currentOrder?.isDeliveryRefundOrder) {
            this.payment_methods_from_config = [
                ...this.payment_methods_from_config,
                ...this.pos.config.urbanpiper_payment_methods_ids,
            ];
        }
    },
});
