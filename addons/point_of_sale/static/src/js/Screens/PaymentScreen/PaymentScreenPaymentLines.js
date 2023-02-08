/** @odoo-module */

import { Component } from "@odoo/owl";

export class PaymentScreenPaymentLines extends Component {
    static template = "PaymentScreenPaymentLines";

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
