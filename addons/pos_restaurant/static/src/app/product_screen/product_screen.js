/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

patch(ProductScreen.prototype, {
    bookTable() {
        this.pos.get_order().setBooked(true);
    },
    showBookButton() {
        return (
            this.pos.config.module_pos_restaurant &&
            this.pos.table &&
            !this.pos.orders.some(
                (o) => o.tableId === this.pos.table.id && o.finalized === false && o.isBooked
            )
        );
    },
});
