/** @odoo-module */

import PosComponent from "@point_of_sale/js/PosComponent";
import Registries from "@point_of_sale/js/Registries";

class PaymentScreenNumpad extends PosComponent {
    setup() {
        super.setup();
        this.decimalPoint = this.env._t.database.parameters.decimal_point;
    }
}
PaymentScreenNumpad.template = "PaymentScreenNumpad";

Registries.Component.add(PaymentScreenNumpad);

export default PaymentScreenNumpad;
