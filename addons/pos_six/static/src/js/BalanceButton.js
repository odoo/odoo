/** @odoo-module */

import { Component } from "@odoo/owl";

export class BalanceButton extends Component {
    static template = "BalanceButton";

    sendBalance() {
        this.env.pos.payment_methods.map((pm) => {
            if (pm.use_payment_terminal === "six") {
                pm.payment_terminal.send_balance();
            }
        });
    }
}
