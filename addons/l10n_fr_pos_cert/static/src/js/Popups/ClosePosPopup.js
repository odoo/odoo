/** @odoo-module */

import { ClosePosPopup } from "@point_of_sale/app/navbar/closing_popup/closing_popup";
import { patch } from "@web/core/utils/patch";

// TODO: remove in master
patch(ClosePosPopup.prototype, {
    sessionIsOutdated() {
        return false;
    },
    canCancel() {
        return super.canCancel(...arguments) && !this.sessionIsOutdated();
    },
});
