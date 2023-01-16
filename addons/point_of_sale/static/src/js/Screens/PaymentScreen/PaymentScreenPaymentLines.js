/** @odoo-module */

import { PosComponent } from "@point_of_sale/js/PosComponent";

export class PaymentScreenPaymentLines extends PosComponent {
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
