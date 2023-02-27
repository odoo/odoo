/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/pos_store";

patch(PosStore.prototype, "pos_hr.PosStore", {
    /**
     * @override
     */
    shouldShowCashControl() {
        if (this.globalState.config.module_pos_hr) {
            return this._super(...arguments) && this.globalState.hasLoggedIn;
        }
        return this._super(...arguments);
    },
});
