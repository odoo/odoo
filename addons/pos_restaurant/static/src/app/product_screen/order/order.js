/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { OrderWidget } from "@point_of_sale/app/screens/product_screen/order/order";
import { AlertPopup } from "@point_of_sale/app/utils/alert_popup/alert_popup";
import { _t } from "@web/core/l10n/translation";

patch(OrderWidget.prototype, "pos_restaurant.OrderWidget", {
    releaseTable() {
        const currentTable = this.pos.table;
        const orderOnTable = this.pos.orders.filter(
            (o) => o.tableId === currentTable.id && o.finalized === false
        );
        const orderOnTableWithOrderline = orderOnTable.find((o) => o.orderlines.length > 0);

        if (orderOnTableWithOrderline) {
            this.popup.add(AlertPopup, {
                title: _t("Open orders"),
                body: _t(
                    "There are open orders on this table. Please close them before releasing the table."
                ),
            });

            return;
        }

        for (const order of orderOnTable) {
            this.pos.removeOrder(order);
        }

        this.pos.showScreen("FloorScreen");
    },
    get showReleaseBtn() {
        if (!this.pos.config.module_pos_restaurant) {
            return false;
        }

        const currentTable = this.pos.table;
        const noEmptyOrderOnTable = this.pos.orders.filter(
            (o) => o.tableId === currentTable.id && o.finalized === false && o.orderlines.length > 0
        );
        return noEmptyOrderOnTable.length ? false : true;
    },
});
