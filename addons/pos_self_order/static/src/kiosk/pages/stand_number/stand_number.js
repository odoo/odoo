/** @odoo-module */

import { Component, useState } from "@odoo/owl";
import { useselfOrder } from "@pos_self_order/kiosk/self_order_kiosk_service";
import { useService } from "@web/core/utils/hooks";
import { KioskTemplate } from "@pos_self_order/kiosk/template/kiosk_template";

export class StandNumber extends Component {
    static template = "pos_self_order.StandNumber";
    static components = { KioskTemplate };

    setup() {
        this.selfOrder = useselfOrder();
        this.selfOrder.isOrder();
        this.router = useService("router");
        this.state = useState({
            standNumber: "",
        });
    }

    numberClick(event) {
        const key = event.target.attributes.data.value;

        if (key === "reset") {
            this.state.standNumber = this.state.standNumber.slice(0, -1);
        } else if (key === "clear") {
            this.state.standNumber = "";
        } else {
            this.state.standNumber += key;
        }
    }

    confirm() {
        if (this.state.standNumber.length > 0) {
            this.selfOrder.tablePadNumber = this.state.standNumber;
            this.router.navigate("payment");
        }
    }

    get tableInput() {
        return this.state.standNumber ? this.state.standNumber : "_ _";
    }
}
