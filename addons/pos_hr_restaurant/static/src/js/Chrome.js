/* @odoo-module alias=pos_restaurant_hr.chrome */

import { Chrome } from '@point_of_sale/js/Chrome';
import { patch } from "@web/core/utils/patch";

patch(Chrome.prototype, "pos_hr_restaurant.Chrome", {
    //@override
    _shouldResetIdleTimer() {
        return this._super() && this.state.tempScreen?.name !== 'LoginScreen';
    }
});
