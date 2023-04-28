/** @odoo-module */

import { Component } from "@odoo/owl";

export class PaymentScreenPaymentLines extends Component {
    static template = "PaymentScreenPaymentLines";
    static props = {
        deleteLine: Function,
        paymentLines: Object,
        selectLine: Function,
        sendForceDone: Function,
        sendPaymentCancel: Function,
        sendPaymentRequest: Function,
        sendPaymentReverse: Function,
    };

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
