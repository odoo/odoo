/** @odoo-module */


import { PSNumpadInputButton } from "./PSNumpadInputButton";
import { Component } from "@odoo/owl";

export class PaymentScreenNumpad extends Component {
    static components = { PSNumpadInputButton };
    static template = "PaymentScreenNumpad";

    setup() {
        super.setup();
        this.decimalPoint = this.env._t.database.parameters.decimal_point;
    }
}
