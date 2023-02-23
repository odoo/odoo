/** @odoo-module */

import { LegacyComponent } from "@web/legacy/legacy_component";

import { PSNumpadInputButton } from "./PSNumpadInputButton";

export class PaymentScreenNumpad extends LegacyComponent {
    static components = { PSNumpadInputButton };
    static template = "PaymentScreenNumpad";

    setup() {
        super.setup();
        this.decimalPoint = this.env._t.database.parameters.decimal_point;
    }
}
