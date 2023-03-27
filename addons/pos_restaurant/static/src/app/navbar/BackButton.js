/** @odoo-module */

import { BackButton } from "@point_of_sale/app/navbar/BackButton";
import { ProductScreen } from "@point_of_sale/js/Screens/ProductScreen/ProductScreen";
import { TipScreen } from "@pos_restaurant/js/Screens/TipScreen";
import { patch } from "@web/core/utils/patch";

patch(BackButton.prototype, "pos_restaurant.BackButton", {
    get table() {
        return this.pos.globalState.table;
    },
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
        if (this.pos.mainScreen.component && this.pos.globalState.config.module_pos_restaurant) {
            if (
                (this.pos.mainScreen.component === ProductScreen &&
                    this.pos.globalState.mobile_pane == "right") ||
                this.pos.mainScreen.component === TipScreen
            ) {
                if (this.table) {
                    const orders = this.pos.globalState.get_order_list();
                    const tableOrders = orders.filter((order) => order.tableId === this.table.id);
                    const qtyChange = tableOrders.reduce(
                        (acc, order) => {
                            const quantityChange = order.getOrderChanges();
                            const quantitySkipped = order.getOrderChanges(true);
                            acc.changed += quantityChange.count;
                            acc.skipped += quantitySkipped.count;
                            return acc;
                        },
                        { changed: 0, skipped: 0 }
                    );

                    this.table.changes_count = qtyChange.changed;
                    this.table.skip_changes = qtyChange.skipped;
                }

                this.pos.showScreen("FloorScreen", { floor: this.floor });
            } else {
                this.pos.globalState.mobile_pane = "right";
                this.pos.showScreen("ProductScreen");
            }
        } else {
            this.pos.globalState.mobile_pane = "right";
            this.pos.showScreen("ProductScreen");
        }
    },
});
