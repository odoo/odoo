/** @odoo-module */

import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/receipt";
import { patch } from "@web/core/utils/patch";

patch(OrderReceipt.prototype, "l10n_pt_pos.OrderReceipt", {
    get receiptEnv() {
        const receipt_render_env = this._super(...arguments);
        const receipt = receipt_render_env.receipt;
        const country = receipt_render_env.order.pos.company.country;
        receipt.is_country_portugal = country && country.code === 'PT';
        if (receipt.is_country_portugal && receipt.l10n_pt_pos_inalterable_hash) {
            receipt.l10n_pt_pos_inalterable_hash_short = receipt.l10n_pt_pos_inalterable_hash.split("$").at(-1);
        }
        return receipt_render_env;
    },
});
