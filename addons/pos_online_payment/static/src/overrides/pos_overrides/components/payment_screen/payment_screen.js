import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { serializeDateTime } from "@web/core/l10n/dates";

patch(PaymentScreen.prototype, {
<<<<<<< 8e25224f791f6ff2e70c386df6848403938efe37
    async validateOrder(isForceValidate) {
        // Order will be now synced on validate order if online payment is configured.
        const opts = this.validationOptions;
        if (
            !this.currentOrder.isSynced &&
            (opts.fastPaymentMethod?.is_online_payment ||
                this.paymentLines.find((p) => p.payment_method_id.is_online_payment))
        ) {
||||||| a893a307689d17f4d0a59d96b566e1dcdf17707f
    async addNewPaymentLine(paymentMethod) {
        if (paymentMethod.is_online_payment && !this.currentOrder.isSynced) {
=======
    async addNewPaymentLine(paymentMethod) {
        // Sync the order to the server only for the first online payment line: syncing a
        // draft order strips its online payment lines, wiping previously added ones.
        const hasOnlinePaymentLine = this.paymentLines.some(
            (line) => line.payment_method_id.is_online_payment
        );
        if (paymentMethod.is_online_payment && !hasOnlinePaymentLine) {
>>>>>>> 4dfb598ec7af14fba8d22086ce5d07ba9a18c1e4
            this.currentOrder.date_order = serializeDateTime(luxon.DateTime.now());
            this.pos.addPendingOrder([this.currentOrder.id]);
            await this.pos.syncAllOrders();
        }
        await super.validateOrder(isForceValidate);
    },
});
