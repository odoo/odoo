/** @odoo-module */

import { Component } from "@odoo/owl";
import { ProductScreen } from "@point_of_sale/js/Screens/ProductScreen/ProductScreen";
import { useService } from "@web/core/utils/hooks";

export class SaveButton extends Component {
    static template = "point_of_sale.SaveButton";
    
    setup() {
        super.setup();
        this.notification = useService("pos_notification");
    }
    onClick() {
        const orderline = this.env.pos.get_order().get_selected_orderline();
        if (!orderline) {
            this.notification.add(
                _.str.sprintf(
                    this.env._t('You cannot save an empty order')
                ),
                3000
            );
            return;
        }
        this._selectEmptyOrder();
        this.notification.add(
            _.str.sprintf(
                this.env._t('Order saved for later')
            ),
            3000
        );
    }
    _selectEmptyOrder() {
        const orders = this.env.pos.get_order_list();
        let emptyOrders = orders.filter((order) => order.is_empty());
        if (emptyOrders.length > 0) {
            this.env.pos.sendDraftToServer();
            this.env.pos.set_order(emptyOrders[0]);
        } else {
            this.env.pos.add_new_order();
        }
    }

}

ProductScreen.addControlButton({
    component: SaveButton,
    condition: function () {
        return this.env.pos.config.trusted_config_ids.length > 0;
    },
});
