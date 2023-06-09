/** @odoo-module */

import { ClosePosPopup } from "@point_of_sale/app/navbar/closing_popup/closing_popup";
import { patch } from "@web/core/utils/patch";

patch(ClosePosPopup.prototype, "l10n_fr_pos_cert.ClosePosPopup", {
    sessionIsOutdated() {
        let isOutdated = false;
        if (this.pos.is_french_country() && this.pos.pos_session.start_at) {
            const now = Date.now();
            const limitDate = new Date(this.pos.pos_session.start_at);
            limitDate.setDate(limitDate.getDate() + 1);
            isOutdated = limitDate < now;
        }
        return isOutdated;
    },
    canCancel() {
        return this._super(...arguments) && !this.sessionIsOutdated();
    },
});
