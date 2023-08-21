
/** @odoo-module */

import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { patch } from "@web/core/utils/patch";

patch(ReceiptScreen.prototype, "l10n_pt_pos.ReceiptScreen", {
    async printReceipt() {
        const _super = this._super;
        if (this.pos.is_portuguese_country() && !this.currentOrder.get_l10n_pt_pos_qr_code_str()) {
            const values = await this.pos.l10n_pt_pos_compute_missing_hashes();
            if (values) {
                this.currentOrder.set_l10n_pt_pos_inalterable_hash(values.hash);
                this.currentOrder.set_l10n_pt_pos_atcud(values.atcud);
                this.currentOrder.set_l10n_pt_pos_qr_code_str(values.qr_code_str);
            }
            // We need to re-render the screen to display the QR code after the RPC call
            await this.render(true);
            // We need to wait for the next tick before printing
            await new Promise((resolve) => window.requestAnimationFrame(resolve));
            await new Promise((resolve) => setTimeout(resolve));
        }
        return _super(...arguments);
    },
});
