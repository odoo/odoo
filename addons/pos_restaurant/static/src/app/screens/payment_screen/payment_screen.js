import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { ask } from "@point_of_sale/app/utils/make_awaitable_dialog";

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
        const changedTables = this.currentOrder?.table_id?.children?.map((table) => table.id);
        // After the order has been validated the tables have no reason to be merged anymore.
        if (changedTables?.length) {
            this.pos.data.write("restaurant.table", changedTables, { parent_id: null });
        }
        return await super.afterOrderValidation(...arguments);
    },
    async validateOrder(isForceValidate) {
        if (this.pos.config.module_pos_restaurant && this.pos.getOrder().hasChange) {
            const confirmed = await ask(this.dialog, {
                title: _t("Warning !"),
                body: _t(
                    "It seems that the order has not been sent. Would you like to send it to preparation?"
                ),
                confirmLabel: _t("Order"),
                cancelLabel: _t("Discard"),
            });
            if (confirmed) {
                await this.pos.sendOrderInPreparationUpdateLastChange(this.currentOrder);
            }
        }
        await super.validateOrder(...arguments);
    },
});
