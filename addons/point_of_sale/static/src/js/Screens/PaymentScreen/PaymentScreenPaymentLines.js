/** @odoo-module */

import { LegacyComponent } from "@web/legacy/legacy_component";

export class PaymentScreenPaymentLines extends LegacyComponent {
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
