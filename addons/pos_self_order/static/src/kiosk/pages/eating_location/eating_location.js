/** @odoo-module */

import { Component, useState } from "@odoo/owl";
import { useSelfOrderKiosk } from "@pos_self_order/kiosk/self_order_kiosk_service";
import { useService } from "@web/core/utils/hooks";

export class EatingLocation extends Component {
    static template = "pos_self_order.EatingLocation";
    static components = {};

    setup() {
        this.selfOrderKiosk = useSelfOrderKiosk();
        this.router = useService("router");
        this.state = useState({
            start: false,
        });
    }

    back() {
        this.router.navigate("default");
    }

    selectLocation(loc) {
        this.selfOrderKiosk.eatingLocation = loc;
        this.router.navigate("product_list");
    }
}
