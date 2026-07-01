import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { serializeDateTime } from "@web/core/l10n/dates";

patch(PaymentScreen.prototype, {
    async addNewPaymentLine(paymentMethod) {
<<<<<<< a893a307689d17f4d0a59d96b566e1dcdf17707f
        if (paymentMethod.is_online_payment && !this.currentOrder.isSynced) {
||||||| 170025fb985b38fee763b0f9f21ce83f7424817c
        if (paymentMethod.is_online_payment && typeof this.currentOrder.id === "string") {
=======
        // Sync the order to the server only for the first online payment line: syncing a
        // draft order strips its online payment lines, wiping previously added ones.
        const hasOnlinePaymentLine = this.paymentLines.some(
            (line) => line.payment_method_id.is_online_payment
        );
        if (paymentMethod.is_online_payment && !hasOnlinePaymentLine) {
>>>>>>> 82e3bbea5d679e219d52988ca96909f310b5268e
            this.currentOrder.date_order = serializeDateTime(luxon.DateTime.now());
            this.pos.addPendingOrder([this.currentOrder.id]);
            await this.pos.syncAllOrders();
        }
        return await super.addNewPaymentLine(...arguments);
    },
});
