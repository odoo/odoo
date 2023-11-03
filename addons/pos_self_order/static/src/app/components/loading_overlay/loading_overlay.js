/** @odoo-module */

import { Component, onWillStart, useState } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/self_order_service";

export class LoadingOverlay extends Component {
    static template = "pos_self_order.LoadingOverlay";
    static props = ["action", "removeTopClasses?"];

    setup() {
        this.selfOrder = useSelfOrder();
        this.state = useState({
            loading: false,
        });

        onWillStart(() => {
            setTimeout(() => {
                this.state.loading = true;
            }, 200);
        });
    }
}
