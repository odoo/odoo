/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";

patch(ReceiptScreen.prototype, {
    async _sendReceiptToCustomer({ action }) {
        if (this.pos.isPortugueseCompany()) {
            await this.pos.l10nPtComputeMissingHashes();
        }
        return super._sendReceiptToCustomer(...arguments);
    },
});
