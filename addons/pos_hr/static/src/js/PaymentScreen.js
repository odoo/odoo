/** @odoo-module */

import PaymentScreen from "@point_of_sale/js/Screens/PaymentScreen/PaymentScreen";
import Registries from "@point_of_sale/js/Registries";

const PosHrPaymentScreen = (PaymentScreen_) =>
    class extends PaymentScreen_ {
        async _finalizeValidation() {
            this.currentOrder.employee = this.env.pos.get_cashier();
            await super._finalizeValidation();
        }
    };

Registries.Component.extend(PaymentScreen, PosHrPaymentScreen);

export default PaymentScreen;
