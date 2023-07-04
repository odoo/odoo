/** @odoo-module */

import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/receipt";
import { patch } from "@web/core/utils/patch";

patch(OrderReceipt.prototype, {
    get receiptEnv() {
        const receipt_render_env = super.receiptEnv;
        const receipt = receipt_render_env.receipt;
        const country = receipt_render_env.order.pos.company.country;
        receipt.is_gcc_country = country
            ? ["SA", "AE", "BH", "OM", "QA", "KW"].includes(country && country.code)
            : false;
        return receipt_render_env;
    },
});
