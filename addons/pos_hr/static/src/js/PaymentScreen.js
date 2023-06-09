/** @odoo-module */

import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreen.prototype, "pos_hr.PaymentScreen", {
    async _finalizeValidation() {
        this.currentOrder.cashier = this.pos.get_cashier();
        await this._super(...arguments);
    },
});
