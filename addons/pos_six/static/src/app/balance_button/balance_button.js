import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";

export class BalanceButton extends Component {
    static template = "pos_six.BalanceButton";
    static props = {};

    setup() {
        this.pos = usePos();
    }
    sendBalance() {
        this.pos.models["pos.payment.method"].forEach((pm) => {
            if (pm.use_payment_terminal === "six") {
                pm.payment_terminal.send_balance();
            }
        });
    }
}
