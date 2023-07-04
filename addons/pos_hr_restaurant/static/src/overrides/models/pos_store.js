/* @odoo-module */

import { patch } from "@web/core/utils/patch";
import "@pos_restaurant/overrides/models/pos_store";
import { PosStore } from "@point_of_sale/app/store/pos_store";

patch(PosStore.prototype, {
    shouldResetIdleTimer() {
        return this.tempScreen?.name !== "LoginScreen" && super.shouldResetIdleTimer(...arguments);
    },
});
