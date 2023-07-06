
/** @odoo-module */

import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { patch } from "@web/core/utils/patch";

patch(ReceiptScreen.prototype, "l10n_pt_pos.ReceiptScreen", {
    async printReceipt() {
        const _super = this._super;
        if (this.pos.is_portuguese_country() && !this.currentOrder.get_l10n_pt_pos_qr_code_str()) {
            const values = await this.pos.l10n_pt_pos_compute_missing_hashes();
            debugger;
            this.currentOrder.set_l10n_pt_pos_inalterable_hash(values.hash);
            this.currentOrder.set_l10n_pt_pos_atcud(values.atcud);
            this.currentOrder.set_l10n_pt_pos_qr_code_str(values.qr_code_str);
            await this.render(true);
        }
        setTimeout(() => {
          _super(...arguments);
        }, 500);  // Wait for the receipt to be rendered since await doesn't
    },
});
