/** @odoo-module */

import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";
import { patch } from "@web/core/utils/patch";

patch(OrderPaymentValidation.prototype, {
    shouldDownloadInvoice() {
        return this.pos.isPortugueseCompany() ? false : super.shouldDownloadInvoice();
    },
});
