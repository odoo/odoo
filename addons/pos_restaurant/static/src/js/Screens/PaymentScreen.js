/** @odoo-module */

import { PaymentScreen } from "@point_of_sale/js/Screens/PaymentScreen/PaymentScreen";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreen.prototype, "pos_restaurant.PaymentScreen", {
    setup() {
        this._super(...arguments);
    },
    get nextScreen() {
        const order = this.currentOrder;
        if (!this.pos.globalState.config.set_tip_after_payment || order.is_tipped) {
            return this._super(...arguments);
        }
        // Take the first payment method as the main payment.
        const mainPayment = order.get_paymentlines()[0];
        if (mainPayment.canBeAdjusted()) {
            return "TipScreen";
        }
        return this._super(...arguments);
    },
});
