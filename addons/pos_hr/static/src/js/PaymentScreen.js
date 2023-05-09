/** @odoo-module */

import { PaymentScreen } from "@point_of_sale/js/Screens/PaymentScreen/PaymentScreen";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreen.prototype, "pos_hr.PaymentScreen", {
    async _finalizeValidation() {
        this.currentOrder.cashier = this.pos.globalState.get_cashier();
        await this._super(...arguments);
    },
});
