/** @odoo-module */

import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/receipt";
import { patch } from "@web/core/utils/patch";

patch(OrderReceipt.prototype, "l10n_pt_pos.OrderReceipt", {
    _l10n_pt_pos_get_qr_code_data(l10n_pt_pos_qr_code_str) {
        const codeWriter = new window.ZXing.BrowserQRCodeSvgWriter();
        const qr_code_svg = new XMLSerializer().serializeToString(
            codeWriter.write(l10n_pt_pos_qr_code_str, 200, 200)
        );
        return "data:image/svg+xml;base64," + window.btoa(qr_code_svg);
    },
    get receiptEnv() {
        const receipt_render_env = this._super(...arguments);
        const receipt = receipt_render_env.receipt;
        const country = receipt_render_env.order.pos.company.country;
        receipt.is_country_portugal = country && country.code === 'PT';
        if (receipt.is_country_portugal && receipt.l10n_pt_pos_inalterable_hash) {
            receipt.l10n_pt_pos_inalterable_hash_short = receipt.l10n_pt_pos_inalterable_hash.split("$").at(-1);
            receipt.l10n_pt_pos_qr_code = this._l10n_pt_pos_get_qr_code_data(receipt.l10n_pt_pos_qr_code_str);
        }
        return receipt_render_env;
    },
});
