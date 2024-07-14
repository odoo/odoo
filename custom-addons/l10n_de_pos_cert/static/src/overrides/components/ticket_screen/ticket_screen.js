/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { patch } from "@web/core/utils/patch";

patch(TicketScreen.prototype, {
    // @Override
    async _onBeforeDeleteOrder(order) {
        try {
            if (this.pos.isCountryGermanyAndFiskaly() && order.isTransactionStarted()) {
                await order.cancelTransaction();
            }
            return super._onBeforeDeleteOrder(...arguments);
        } catch (error) {
            this._triggerFiskalyError(error);
            return false;
        }
    },
    _triggerFiskalyError(error) {
        const message = {
            noInternet: _t(
                "Check the internet connection then try to validate or cancel the order. " +
                    "Do not delete your browsing, cookies and cache data in the meantime!"
            ),
            unknown: _t(
                "An unknown error has occurred! Try to validate this order or cancel it again. " +
                    "Please contact Odoo for more information."
            ),
        };
        this.pos.fiskalyError(error, message);
    },
});
