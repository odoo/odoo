import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreen.prototype, {
    async addNewPaymentLine(paymentMethod) {
        if (paymentMethod.is_online_payment && typeof this.currentOrder.id === "string") {
            this.currentOrder.date_order = luxon.DateTime.now().toFormat("yyyy-MM-dd HH:mm:ss");
            this.pos.addPendingOrder([this.currentOrder.id]);
            await this.pos.syncAllOrders();
        }
        return await super.addNewPaymentLine(...arguments);
    },
});
