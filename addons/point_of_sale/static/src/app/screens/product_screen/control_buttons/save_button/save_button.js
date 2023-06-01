/** @odoo-module */

import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/pos_hook";
import { ProductScreen } from "@point_of_sale/js/Screens/ProductScreen/ProductScreen";
import { useService } from "@web/core/utils/hooks";

export class SaveButton extends Component {
    static template = "point_of_sale.SaveButton";

    setup() {
        this.pos = usePos();
        this.notification = useService("pos_notification");
    }
    onClick() {
        const orderline = this.pos.globalState.get_order().get_selected_orderline();
        if (!orderline) {
            this.notification.add(this.env._t("You cannot save an empty order"), 3000);
            return;
        }
        this._selectEmptyOrder();
        this.notification.add(this.env._t("Order saved for later"), 3000);
    }
    _selectEmptyOrder() {
        const { globalState } = this.pos;
        const orders = globalState.get_order_list();
        const emptyOrders = orders.filter((order) => order.is_empty());
        if (emptyOrders.length > 0) {
            globalState.sendDraftToServer();
            globalState.set_order(emptyOrders[0]);
        } else {
            globalState.add_new_order();
        }
    }
}

ProductScreen.addControlButton({
    component: SaveButton,
    condition: function () {
        return this.pos.globalState.config.trusted_config_ids.length > 0;
    },
});
