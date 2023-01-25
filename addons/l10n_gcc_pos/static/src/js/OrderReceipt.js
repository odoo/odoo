/** @odoo-module */

import { OrderReceipt } from "@point_of_sale/js/Screens/ReceiptScreen/OrderReceipt";
import { patch } from "@web/core/utils/patch";

patch(OrderReceipt.prototype, "l10n_gcc_pos.OrderReceipt", {
    get receiptEnv() {
        const receipt_render_env = this._super(...arguments);
        const receipt = receipt_render_env.receipt;
        const country = receipt_render_env.order.pos.company.country;
        receipt.is_gcc_country = ["SA", "AE", "BH", "OM", "QA", "KW"].includes(
            country && country.code
        );
        return receipt_render_env;
    },
});
