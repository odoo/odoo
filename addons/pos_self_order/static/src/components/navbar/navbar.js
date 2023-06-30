/** @odoo-module */

import { Component } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/self_order_service";
import { useService } from "@web/core/utils/hooks";
export class NavBar extends Component {
    static template = "pos_self_order.NavBar";
    static props = {
        customText: { type: String, optional: true },
        class: { type: String, optional: true },
    };
    static defaultProps = { class: "" };

    setup() {
        this.router = useService("router");
        this.selfOrder = useSelfOrder();
    }
}
