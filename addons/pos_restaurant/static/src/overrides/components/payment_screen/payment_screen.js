import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreen.prototype, {
    get nextScreen() {
        const order = this.currentOrder;
        if (!this.pos.config.set_tip_after_payment || order.is_tipped) {
            return super.nextScreen;
        }
        // Take the first payment method as the main payment.
        const mainPayment = order.payment_ids[0];
        if (mainPayment && mainPayment.canBeAdjusted()) {
            return "TipScreen";
        }
        return super.nextScreen;
    },
    async afterOrderValidation(suggestToSync = true) {
        // After the order has been validated the tables have no reason to be merged anymore.
        const changedTables = this.pos.models["restaurant.table"]?.filter(
            (t) => t.parent_id && t.parent_id.id === this.currentOrder.table_id?.id
        );
        if (changedTables?.length) {
            for (const table of changedTables) {
                this.pos.data.write("restaurant.table", [table.id], { parent_id: null });
            }
        }
        return await super.afterOrderValidation(...arguments);
    },
});
