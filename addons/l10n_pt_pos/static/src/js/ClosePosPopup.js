/** @odoo-module */

import { ClosePosPopup } from "@point_of_sale/app/navbar/closing_popup/closing_popup";
import { patch } from "@web/core/utils/patch";

patch(ClosePosPopup.prototype, "l10n_pt_pos.ClosePosPopup", {
    async closeSession() {
        const _super = this._super;
        if (this.pos.is_portuguese_country()) {
            await this.pos.l10n_pt_compute_missing_hashes();
        }
        return _super(...arguments);
    },
});
