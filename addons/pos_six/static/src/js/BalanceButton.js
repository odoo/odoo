/** @odoo-module */

import { LegacyComponent } from "@web/legacy/legacy_component";

export class BalanceButton extends LegacyComponent {
    static template = "BalanceButton";

    sendBalance() {
        this.env.pos.payment_methods.map((pm) => {
            if (pm.use_payment_terminal === "six") {
                pm.payment_terminal.send_balance();
            }
        });
    }
}
