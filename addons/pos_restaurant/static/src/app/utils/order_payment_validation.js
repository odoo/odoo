import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";
import { patch } from "@web/core/utils/patch";

patch(OrderPaymentValidation.prototype, {
    get nextPage() {
        if (!this.pos.config.set_tip_after_payment || this.order.is_tipped) {
            return super.nextPage;
        }
        // Take the first payment method as the main payment.
        const mainPayment = this.order.payment_ids[0];
        if (mainPayment && mainPayment.canBeAdjusted()) {
            return {
                page: "TipScreen",
                params: {
                    orderUuid: this.order.uuid,
                },
            };
        }
        return super.nextPage;
    },
    async afterOrderValidation(suggestToSync = true) {
        const changedTables = this.order?.table_id?.children?.map((table) => table.id);
        // After the order has been validated the tables have no reason to be merged anymore.
        if (changedTables?.length) {
            this.pos.data.write("restaurant.table", changedTables, { parent_id: null });
        }
        return await super.afterOrderValidation(...arguments);
    },
});
