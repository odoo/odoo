import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { serializeDateTime } from "@web/core/l10n/dates";

patch(PaymentScreen.prototype, {
    async addNewPaymentLine(paymentMethod) {
        if (paymentMethod.is_online_payment && !this.currentOrder.isSynced) {
            this.currentOrder.date_order = serializeDateTime(luxon.DateTime.now());
            this.pos.addPendingOrder([this.currentOrder.id]);
            await this.pos.syncAllOrders();
        }
        return await super.addNewPaymentLine(...arguments);
    },
});
