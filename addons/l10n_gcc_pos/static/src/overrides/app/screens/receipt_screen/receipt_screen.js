/** @odoo-module */

import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { patch } from "@web/core/utils/patch";

patch(ReceiptScreen.prototype, {
    get receiptData() {
        const receiptData = super.receiptData;
        const receipt = receiptData.receipt;
        const country = receiptData.order.pos.company.country;
        receipt.is_gcc_country = country
            ? ["SA", "AE", "BH", "OM", "QA", "KW"].includes(country && country.code)
            : false;
        return receiptData;
    },
});
