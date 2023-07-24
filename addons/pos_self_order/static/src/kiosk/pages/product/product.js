/** @odoo-module */

import { Component } from "@odoo/owl";
import { useSelfOrderKiosk } from "@pos_self_order/kiosk/self_order_kiosk_service";

export class Product extends Component {
    static template = "pos_self_order.Product";
    static props = ["product"];

    setup() {
        this.selfOrderKiosk = useSelfOrderKiosk();
    }
}
