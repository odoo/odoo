/** @odoo-module */

import { ClosePosPopup } from "@point_of_sale/app/navbar/closing_popup/closing_popup";
import { patch } from "@web/core/utils/patch";

// TODO: remove in master (saas-18.5)
patch(ClosePosPopup.prototype, {
    sessionIsOutdated() {
        return false;
    },
});
