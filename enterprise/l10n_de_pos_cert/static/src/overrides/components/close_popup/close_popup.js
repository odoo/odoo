/** @odoo-module */

import { ClosePosPopup } from "@point_of_sale/app/navbar/closing_popup/closing_popup";
import { patch } from "@web/core/utils/patch";

patch(ClosePosPopup.prototype, {
    async closeSession() {
        if (this.pos.isCountryGermanyAndFiskaly()) {
            // Cancel all open orders at Fiskaly before closing to prevent them from remaining active,
            // since orders are now registered on creation in JS to maintain correct timing so all of these are active in fiskaly.

            try {
                for (const order of this.pos.get_open_orders()) {
                    await this.pos.handleFiskalyCancellation(order);
                }
                // fetch and cancel all active orders which were removed from cache so remained active on fiskaly
                await this.pos.cancelActiveTransactions();
            } catch (error) {
                this.pos.fiskalyError(error);
            }
        }
        return super.closeSession();
    },
});
