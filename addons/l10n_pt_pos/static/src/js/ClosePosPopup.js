/** @odoo-module */

import { ClosePosPopup } from "@point_of_sale/js/Popups/ClosePosPopup";
import { patch } from "@web/core/utils/patch";

patch(ClosePosPopup.prototype, "l10n_pt_pos.ClosePosPopup", {
    async closeSession() {
        const _super = this._super;
        if (this.env.pos.is_portuguese_country()) {
            await this.env.pos.l10n_pt_compute_missing_hashes();
        }
        return _super(...arguments);
    },
});
