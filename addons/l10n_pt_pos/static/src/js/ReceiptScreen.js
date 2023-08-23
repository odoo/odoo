
/** @odoo-module */

import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { patch } from "@web/core/utils/patch";

patch(ReceiptScreen.prototype, "l10n_pt_pos.ReceiptScreen", {
    async printReceipt() {
        const _super = this._super;
        if (this.pos.isPortugueseCountry() && !this.currentOrder.getL10nPtPosQrCodeStr()) {
            const values = await this.pos.l10nPtPosComputeMissingHashes();
            debugger;
            if (values) {
                this.currentOrder.setL10nPtPosInalterableHash(values.hash);
                this.currentOrder.setL10nPtPosInalterableHashShort(values.hash_short);
                this.currentOrder.setL10nPtPosAtcud(values.atcud);
                this.currentOrder.setL10nPtPosQrCodeStr(values.qr_code_str);
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
