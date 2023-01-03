/** @odoo-module */

import PosComponent from "@point_of_sale/js/PosComponent";
import Registries from "@point_of_sale/js/Registries";

class BalanceButton extends PosComponent {
    sendBalance() {
        this.env.pos.payment_methods.map((pm) => {
            if (pm.use_payment_terminal === "six") {
                pm.payment_terminal.send_balance();
            }
        });
    }
}
BalanceButton.template = "BalanceButton";

Registries.Component.add(BalanceButton);

export default BalanceButton;
