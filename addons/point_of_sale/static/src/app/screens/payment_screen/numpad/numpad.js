/** @odoo-module */

import { PSNumpadInputButton } from "@point_of_sale/app/screens/payment_screen/numpad/numpad_button/numpad_button";
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
