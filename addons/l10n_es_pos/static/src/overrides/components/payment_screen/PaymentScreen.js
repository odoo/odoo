/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";

patch(PaymentScreen.prototype, {
    async validateOrder(isForceValidate) {
        if (!this.pos.config.is_spanish) {
            await super.validateOrder(...arguments);
            return;
        }
        const below_limit =
            this.currentOrder.get_total_with_tax() <=
            this.pos.config.l10n_es_simplified_invoice_limit;
        const order = this.currentOrder;
        if (below_limit && !order.to_invoice) {
            await order.set_simple_inv_number();
        } else {
            // Force invoice above limit. Online is needed.
            order.to_invoice = true;
        }
        await super.validateOrder(...arguments);
    },
});
