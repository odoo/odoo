/* @odoo-module alias=pos_restaurant_hr.chrome */

import { patch } from "@web/core/utils/patch";
import "@pos_restaurant/app/pos_store";
import { PosStore } from "@point_of_sale/app/pos_store";

patch(PosStore.prototype, "pos_hr_restaurant.PosStore", {
    shouldResetIdleTimer() {
        return this.tempScreen?.name !== "LoginScreen" && this._super(...arguments);
    },
});
