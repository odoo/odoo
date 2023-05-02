/** @odoo-module */

import { Component } from "@odoo/owl";

export class PaymentScreenPaymentLines extends Component {
    static template = "PaymentScreenPaymentLines";

    formatLineAmount(paymentline) {
        return this.env.utils.formatCurrency(paymentline.get_amount(), false);
    }
    selectedLineClass(line) {
        return { "payment-terminal": line.get_payment_status() };
    }
    unselectedLineClass(line) {
        return {};
    }
}
