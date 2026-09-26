import { useEffect } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";

patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);

        useEffect(() => {
            // The paid order status will be sent from the server via the bus,
            // so we need to validate the order locally when we detect it.
            const order = this.currentOrder.payment_ids;
            const onlinePayment = order.some((pl) => pl.payment_method_id.type === "online");
            if (onlinePayment && order.state === "paid" && !this.editMode) {
                this.pos.validateOrder();
            }
        });
    },
    get configPaymentMethods() {
        let configMethods = super.configPaymentMethods;
        // don't allow to update and edit and pay with online payments
        if (this.currentOrder.state === "paid") {
            configMethods = configMethods.filter((pm) => pm.type !== "online");
        }
        return configMethods;
    },
    updateSelectedPaymentline() {
        if (
            this.selectedPaymentLine?.payment_method_id?.type === "online" &&
            this.currentOrder.state === "paid"
        ) {
            return;
        }
        super.updateSelectedPaymentline(...arguments);
    },
});
