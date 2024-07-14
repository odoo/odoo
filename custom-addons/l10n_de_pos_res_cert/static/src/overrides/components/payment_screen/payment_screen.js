/** @odoo-module */

import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreen.prototype, {
    //@Override
    async _finalizeValidation() {
        if (this.pos.isRestaurantCountryGermanyAndFiskaly()) {
            try {
                await this.currentOrder.retrieveAndSendLineDifference();
            } catch {
                // do nothing with the error
            }
        }
        await super._finalizeValidation(...arguments);
    },
});
