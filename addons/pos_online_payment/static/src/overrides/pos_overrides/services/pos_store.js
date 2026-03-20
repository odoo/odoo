import { patch } from "@web/core/utils/patch";
import { serializeDateTime } from "@web/core/l10n/dates";
import { PosStore } from "@point_of_sale/app/services/pos_store";

patch(PosStore.prototype, {
    async validateOrder(args = {}) {
        const { order = this.getOrder() } = args;

        // Order will be now synced on validate order if online payment is configured.
        const opts = this.getValidationOrderOptions({ order });
        if (
            !order.isSynced &&
            (opts.fastPaymentMethod?.type === "online" ||
                order.payment_ids.find((p) => p.payment_method_id.type === "online"))
        ) {
            order.date_order = serializeDateTime(luxon.DateTime.now());
            this.addPendingOrder([order.id]);
            await this.syncAllOrders();
        }
        return await super.validateOrder({ ...args, order });
    },
});
