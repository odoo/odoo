/** @odoo-module */

import { TicketScreen } from "@point_of_sale/js/Screens/TicketScreen/TicketScreen";
import { patch } from "@web/core/utils/patch";
import { ErrorPopup } from "@point_of_sale/js/Popups/ErrorPopup";

patch(TicketScreen.prototype, "l10n_fr_pos_cert.TicketScreen", {
    // @Override
    async _onBeforeDeleteOrder(order) {
        if (this.pos.globalState.is_french_country()) {
            this.popup.add(ErrorPopup, {
                title: this.env._t("Forbidden to remove order"),
                body: this.env._t("It is not allowed to remove an order.")
            });
            return false;
        }
        return this._super(...arguments);
    },
    shouldHideDeleteButton(order) {
        return this.pos.globalState.is_french_country() ? true : this._super(...arguments);;
    }
});
