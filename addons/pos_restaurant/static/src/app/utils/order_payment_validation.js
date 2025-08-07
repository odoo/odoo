import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";
import { patch } from "@web/core/utils/patch";
import { ask } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { _t } from "@web/core/l10n/translation";

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
    async askBeforeValidation() {
        if (this.pos.config.module_pos_restaurant && this.order.hasChange && !this.order.isRefund) {
            const confirmed = await ask(this.pos.dialog, {
                title: _t("Warning !"),
                body: _t(
                    "It seems that the order has not been sent. Would you like to send it to preparation?"
                ),
                confirmLabel: _t("Order"),
                cancelLabel: _t("Discard"),
            });
            if (confirmed) {
                if (!this.pos.isFastPaymentRunning) {
                    await this.pos.sendOrderInPreparationUpdateLastChange(this.order);
                } else {
                    this.pos.pushOrderToPreparation = true;
                }
            }
        }
        return await super.askBeforeValidation();
    },
});
