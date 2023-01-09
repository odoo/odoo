/** @odoo-module */

import PosComponent from "@point_of_sale/js/PosComponent";
import Registries from "@point_of_sale/js/Registries";

class PaymentScreenPaymentLines extends PosComponent {
    formatLineAmount(paymentline) {
        return this.env.pos.format_currency_no_symbol(paymentline.get_amount());
    }
    selectedLineClass(line) {
        return { "payment-terminal": line.get_payment_status() };
    }
    unselectedLineClass(line) {
        return {};
    }
}
PaymentScreenPaymentLines.template = "PaymentScreenPaymentLines";

Registries.Component.add(PaymentScreenPaymentLines);

export default PaymentScreenPaymentLines;
