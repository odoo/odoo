import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";
import { patch } from "@web/core/utils/patch";
import { RPCError } from "@web/core/network/rpc";

patch(OrderPaymentValidation.prototype, {
    async validateOrder(isForceValidate) {
        await this.pos.ensureGuestCustomerCount(this.pos.getOrder());
        return await super.validateOrder(...arguments);
    },
    async finalizeValidation() {
        const isFirstValidation = !this.order.finalized;
        const originOrder = this.order.split_origin_order_id;
        const result = await super.finalizeValidation(...arguments);
        const validated = result !== false && !(result instanceof RPCError);
        if (originOrder && isFirstValidation && validated) {
            await this.pos.applySplitPaymentShares(originOrder, this.order.amountPaid);
        }
        return result;
    },
    async afterOrderValidation(suggestToSync = true) {
        // A split payment order borrows the origin table: the table is still in use.
        const changedTables = this.order.isSplitPaymentOrder
            ? undefined
            : this.order?.table_id?.children?.map((table) => table.id);
        // After the order has been validated the tables have no reason to be merged anymore.
        if (changedTables?.length) {
            this.pos.data.write("restaurant.table", changedTables, { parent_id: null });
        }
        return await super.afterOrderValidation(...arguments);
    },
});
