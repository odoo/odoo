/** @odoo-module */

import { Component } from "@odoo/owl";
import { useSelfOrderKiosk } from "@pos_self_order/kiosk/self_order_kiosk_service";
import { useService } from "@web/core/utils/hooks";

export class LandingPage extends Component {
    static template = "pos_self_order.LandingPage";
    static components = {};

    setup() {
        this.selfOrderKiosk = useSelfOrderKiosk();
        this.router = useService("router");
    }

    start(mode) {
        this.router.navigate("location");
    }
}
