/** @odoo-module */

import { PosComponent } from "@point_of_sale/js/PosComponent";

export class BalanceButton extends PosComponent {
    static template = "BalanceButton";

    sendBalance() {
        this.env.pos.payment_methods.map((pm) => {
            if (pm.use_payment_terminal === "six") {
                pm.payment_terminal.send_balance();
            }
        });
    }
}
