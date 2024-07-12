/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";

patch(ControlButtons.prototype, {
    async clickRefund() {
        if (this.pos.isPortugueseCompany()) {
            await this.pos.l10nPtComputeMissingHashes();
        }
        return super.clickRefund(...arguments);
    },
});
