import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { serializeDateTime } from "@web/core/l10n/dates";

patch(PaymentScreen.prototype, {
    async addNewPaymentLine(paymentMethod) {
        // Sync the order to the server only for the first online payment line: syncing a
        // draft order strips its online payment lines, wiping previously added ones.
        const hasOnlinePaymentLine = this.paymentLines.some(
            (line) => line.payment_method_id.is_online_payment
        );
        if (paymentMethod.is_online_payment && !hasOnlinePaymentLine) {
            this.currentOrder.date_order = serializeDateTime(luxon.DateTime.now());
            this.pos.addPendingOrder([this.currentOrder.id]);
            await this.pos.syncAllOrders();
        }
        return await super.addNewPaymentLine(...arguments);
    },
});
