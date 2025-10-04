import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";

patch(PaymentScreen.prototype, {
    /**
     * @override
     */
    setup() {
        super.setup();
        this.refundedOrder = this.currentOrder.refunded_order_id;
        if (
            this.refundedOrder?.source === "mobile" &&
            this.refundedOrder?.payment_ids[0].online_account_payment_id &&
            !this.payment_methods_from_config.some(
                (pm) => pm.id === this.refundedOrder?.payment_ids[0].payment_method_id.id
            )
        ) {
            this.payment_methods_from_config = [
                ...this.payment_methods_from_config,
                this.pos.config.self_order_online_payment_method_id,
            ];
        }
    },
});
