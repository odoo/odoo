/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

patch(ProductScreen.prototype, {
    releaseTable() {
        const orderOnTable = this.pos.orders.filter(
            (o) => o.tableId === this.pos.table.id && o.finalized === false
        );
        for (const order of orderOnTable) {
            this.pos.removeOrder(order);
        }
        this.pos.showScreen("FloorScreen");
    },
    showReleaseBtn() {
        return (
            this.pos.config.module_pos_restaurant &&
            this.pos.table &&
            !this.pos.orders.some(
                (o) =>
                    o.tableId === this.pos.table.id && o.finalized === false && o.orderlines.length
            )
        );
    },
});
