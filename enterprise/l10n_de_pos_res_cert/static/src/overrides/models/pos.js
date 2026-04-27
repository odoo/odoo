/** @odoo-module */

import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    isRestaurantCountryGermanyAndFiskaly() {
        return this.isCountryGermanyAndFiskaly() && this.config.module_pos_restaurant;
    },
    //@Override
    disallowLineQuantityChange() {
        const result = super.disallowLineQuantityChange(...arguments);
        return this.isRestaurantCountryGermanyAndFiskaly() || result;
    },
});
