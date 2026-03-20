import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";
import { patch } from "@web/core/utils/patch";

patch(OrderPaymentValidation.prototype, {
    async afterOrderValidation(suggestToSync = true) {
        const changedTables = this.order?.table_id?.children?.map((table) => table.id);
        // After the order has been validated the tables have no reason to be merged anymore.
        if (changedTables?.length) {
            this.pos.data.write("restaurant.table", changedTables, { parent_id: null });
        }
        return await super.afterOrderValidation(...arguments);
    },
});
