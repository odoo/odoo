/** @odoo-module */

import { Order } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";

patch(Order.prototype, {
    getOrderReceiptEnv() {
        const receiptData = super.getOrderReceiptEnv();
        const receipt = receiptData.receipt;
        const country = receiptData.order.pos.company.country;
        receipt.is_gcc_country = country
            ? ["SA", "AE", "BH", "OM", "QA", "KW"].includes(country && country.code)
            : false;
        return receiptData;
    },
});
