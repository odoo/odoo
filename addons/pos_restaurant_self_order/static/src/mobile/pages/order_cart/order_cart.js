/** @odoo-module */

import { useState } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { OrderCart } from "@pos_self_order/mobile/pages/order_cart/order_cart";
import { PopupTable } from "@pos_restaurant_self_order/mobile/components/popup_table/popup_table";

OrderCart.components.PopupTable = PopupTable;
patch(OrderCart.prototype, "pos_self_order.OrderCart", {
    setup() {
        this._super();

        this.state = useState({
            selectTable: false,
        });
    },

    async selectTable(table) {
        if (table) {
            this.selfOrder.table = table;
            this.router.addTableIdentifier(table);
            await this.processOrder();
        }
        this.state.selectTable = false;
    },

    async processOrder() {
        if (!this.selfOrder.table) {
            this.state.selectTable = true;
            return;
        }

        this._super(...arguments);
    },
});
