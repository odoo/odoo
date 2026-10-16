/** @odoo-module */

import { onWillStart } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";

patch(ReceiptScreen.prototype, {
    setup() {
        super.setup(...arguments);
        onWillStart(async () => {
            if (this.pos.isPortugueseCompany()) {
                await this.pos.l10nPtPrepareOrderForReceipt(this.currentOrder);
            }
        });
    },

    async _sendReceiptToCustomer() {
        if (this.pos.isPortugueseCompany() && typeof this.currentOrder.id === "number") {
            const prepared = await this.pos.l10nPtPrepareOrderForReceipt(this.currentOrder);
            if (!prepared) {
                return Promise.reject();
            }
        }
        return super._sendReceiptToCustomer(...arguments);
    },
});
