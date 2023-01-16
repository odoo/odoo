/* @odoo-module */

import { PosPopupController } from "@point_of_sale/js/Popups/PosPopupController";
import { useBus } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

patch(PosPopupController.prototype, "pos_restaurant.PosPopupController", {
    setup() {
        this._super(...arguments);
        useBus(this.env.posbus, "close-popups-but-error", this._closePopupsButError);
    },
    _closePopupsButError(event) {
        const { resolve } = event.detail;
        const isErrorPopupOpen = this.popups.some((popup) =>
            popup.name.toLowerCase().includes("error")
        );
        if (!isErrorPopupOpen) {
            for (const popup of this.popups) {
                popup.props.resolve(false);
            }
            this.popups.length = 0; // clearing the array but keep the useState
        }
        resolve(!isErrorPopupOpen);
    },
});
