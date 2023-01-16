/** @odoo-module */

import { PosComponent } from "@point_of_sale/js/PosComponent";

import { PSNumpadInputButton } from "./PSNumpadInputButton";

export class PaymentScreenNumpad extends PosComponent {
    static components = { PSNumpadInputButton };
    static template = "PaymentScreenNumpad";

    setup() {
        super.setup();
        this.decimalPoint = this.env._t.database.parameters.decimal_point;
    }
}
