/** @odoo-module */

import { Component, useState } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/self_order_service";
import { useService } from "@web/core/utils/hooks";

export class StandNumberPage extends Component {
    static template = "pos_self_order.StandNumberPage";

    setup() {
        this.selfOrder = useSelfOrder();
        this.selfOrder.isOrder();
        this.router = useService("router");
        this.state = useState({
            standNumber: "",
        });
    }

    get tableInput() {
        return this.state.standNumber ? this.state.standNumber : "_ _";
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
            this.selfOrder.currentOrder.table_stand_number = this.state.standNumber;
            this.selfOrder.confirmOrder();
        }
    }
}
