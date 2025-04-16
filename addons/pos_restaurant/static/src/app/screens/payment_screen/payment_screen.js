import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreen.prototype, {
    get nextPage() {
        const order = this.currentOrder;
        if (!this.pos.config.set_tip_after_payment || order.is_tipped) {
            return super.nextPage;
        }
        // Take the first payment method as the main payment.
        const mainPayment = order.payment_ids[0];
        if (mainPayment && mainPayment.canBeAdjusted()) {
            return {
                page: "TipScreen",
                params: {
                    orderUuid: order.uuid,
                },
            };
        }
        return super.nextPage;
    },
    async afterOrderValidation(suggestToSync = true) {
        const changedTables = this.currentOrder?.table_id?.children?.map((table) => table.id);
        // After the order has been validated the tables have no reason to be merged anymore.
        if (changedTables?.length) {
            this.pos.data.write("restaurant.table", changedTables, { parent_id: null });
        }
        return await super.afterOrderValidation(...arguments);
    },
});
