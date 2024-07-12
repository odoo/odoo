/** @odoo-module */

import { ClosePosPopup } from "@point_of_sale/app/navbar/closing_popup/closing_popup";
import { patch } from "@web/core/utils/patch";

patch(ClosePosPopup.prototype, {
    async closeSession() {
        if (this.pos.isPortugueseCompany()) {
            await this.pos.l10nPtComputeMissingHashes();
        }
        return super.closeSession(...arguments);
    },
});
