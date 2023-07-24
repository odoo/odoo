/** @odoo-module */

import { Component } from "@odoo/owl";
import { useselfOrder } from "@pos_self_order/kiosk/self_order_kiosk_service";
import { useService } from "@web/core/utils/hooks";
import { KioskTemplate } from "@pos_self_order/kiosk/template/kiosk_template";

export class EatingLocation extends Component {
    static template = "pos_self_order.EatingLocation";
    static components = { KioskTemplate };

    setup() {
        this.selfOrder = useselfOrder();
        this.router = useService("router");
    }

    back() {
        this.router.navigate("default");
    }

    selectLocation(loc) {
        if (loc === "out") {
            this.selfOrder.currentOrder.take_away = true;
        }
        this.router.navigate("product_list");
    }
}
