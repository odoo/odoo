/** @odoo-module */

import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/pos_hook";

export class BalanceButton extends Component {
    static template = "BalanceButton";

    setup() {
        this.pos = usePos();
    }
    sendBalance() {
        this.pos.globalState.payment_methods.forEach((pm) => {
            if (pm.use_payment_terminal === "six") {
                pm.payment_terminal.send_balance();
            }
        });
    }
}
