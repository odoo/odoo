/** @odoo-module */

import { BackButton } from "@point_of_sale/app/navbar/back_button/back_button";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { TipScreen } from "@pos_restaurant/js/Screens/TipScreen";
import { patch } from "@web/core/utils/patch";

patch(BackButton.prototype, "pos_restaurant.BackButton", {
    get floor() {
        return this.table?.floor;
    },
    get hasTable() {
        return this.table != null;
    },
    /**
     * @override
     * If we have a floor screen,
     * the logic of the back button changes a bit.
     */
    async backToFloorScreen() {
        if (this.pos.mainScreen.component && this.pos.config.module_pos_restaurant) {
            if (
                (this.pos.mainScreen.component === ProductScreen &&
                    this.pos.mobile_pane == "right") ||
                this.pos.mainScreen.component === TipScreen
            ) {
                this.pos.showScreen("FloorScreen", { floor: this.floor });
            } else {
                this.pos.mobile_pane = "right";
                this.pos.showScreen("ProductScreen");
            }
        } else {
            this.pos.mobile_pane = "right";
            this.pos.showScreen("ProductScreen");
        }
    },
});
