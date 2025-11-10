import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { serializeDateTime } from "@web/core/l10n/dates";

patch(PaymentScreen.prototype, {
    async validateOrder(isForceValidate) {
        // Order will be now synced on validate order if online payment is configured.
        const opts = this.validationOptions;
        if (
            !this.currentOrder.isSynced &&
            (opts.fastPaymentMethod?.is_online_payment ||
                this.paymentLines.find((p) => p.payment_method_id.is_online_payment))
        ) {
            this.currentOrder.date_order = serializeDateTime(luxon.DateTime.now());
            this.pos.addPendingOrder([this.currentOrder.id]);
            await this.pos.syncAllOrders();
        }
        await super.validateOrder(isForceValidate);
    },
});
