import { RestaurantTable } from "@pos_restaurant/app/models/restaurant_table";
import { patch } from "@web/core/utils/patch";

patch(RestaurantTable.prototype, {
    get isShareable() {
        return super.isShareable || this.module_pos_restaurant;
    },
});
