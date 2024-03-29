/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { useService } from "@web/core/utils/hooks";

export class SaveButton extends Component {
    static template = "point_of_sale.SaveButton";

    setup() {
        this.pos = usePos();
        this.notification = useService("pos_notification");
    }
    onClick() {
        const orderline = this.pos.get_order().get_selected_orderline();
        if (!orderline) {
            this.notification.add(_t("You cannot save an empty order"), 3000);
            return;
        }
        this._selectEmptyOrder();
        this.notification.add(_t("Order saved for later"), 3000);
    }
    _selectEmptyOrder() {
        const orders = this.pos.get_order_list();
        const emptyOrders = orders.filter((order) => order.is_empty());
        if (emptyOrders.length > 0) {
            this.pos.sendDraftToServer();
            this.pos.set_order(emptyOrders[0]);
        } else {
            this.pos.add_new_order();
        }
    }
}

ProductScreen.addControlButton({
    component: SaveButton,
    condition: function () {
        return this.pos.config.trusted_config_ids.length > 0;
    },
});
