/** @odoo-module */

import { Component, useState } from "@odoo/owl";
import { useselfOrder } from "@pos_self_order/kiosk/self_order_kiosk_service";
import { useService } from "@web/core/utils/hooks";
import { KioskTemplate } from "@pos_self_order/kiosk/template/kiosk_template";
import { Numpad } from "@point_of_sale/app/generic_components/numpad/numpad";

export class StandNumber extends Component {
    static template = "pos_self_order.StandNumber";
    static components = { KioskTemplate, Numpad };

    setup() {
        this.selfOrder = useselfOrder();
        this.selfOrder.isOrder();
        this.router = useService("router");
        this.state = useState({
            standNumber: "",
        });
    }

    numberClick(key) {
        if (key === "reset") {
            this.state.standNumber = this.state.standNumber.slice(0, -1);
        } else if (key === "clear") {
            this.state.standNumber = "";
        } else {
            this.state.standNumber += key;
        }
    }

    get numpadButtons() {
        return [
            { value: "1", class: "fs-2" },
            { value: "2", class: "fs-2" },
            { value: "3", class: "fs-2" },
            { value: "4", class: "fs-2" },
            { value: "5", class: "fs-2" },
            { value: "6", class: "fs-2" },
            { value: "7", class: "fs-2" },
            { value: "8", class: "fs-2" },
            { value: "9", class: "fs-2" },
            { value: "clear", text: "x", class: "fs-2" },
            { value: "0", class: "fs-2" },
            { value: "reset", text: "⌫", class: "fs-2" },
        ];
    }

    confirm() {
        if (this.state.standNumber.length > 0) {
            this.selfOrder.tablePadNumber = this.state.standNumber;
            this.selfOrder.initPayment();
        }
    }

    get tableInput() {
        return this.state.standNumber ? this.state.standNumber : "_ _";
    }
}
