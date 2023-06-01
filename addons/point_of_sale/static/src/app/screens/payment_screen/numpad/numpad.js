/** @odoo-module */

import { PSNumpadInputButton } from "./PSNumpadInputButton";
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class PaymentScreenNumpad extends Component {
    static components = { PSNumpadInputButton };
    static template = "PaymentScreenNumpad";

    setup() {
        super.setup();
        this.decimalPoint = useService("localization").decimalPoint;
    }
}
