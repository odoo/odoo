/** @odoo-module */

import { Chrome } from "@point_of_sale/js/Chrome";
import { patch } from "@web/core/utils/patch";
import { ClosePosPopup } from "@point_of_sale/js/Popups/ClosePosPopup";

patch(Chrome.prototype, "l10n_fr_pos_cert.Chrome", {
    async start() {
        await this._super(...arguments);
        if (this.env.pos.is_french_country() && this.env.pos.pos_session.start_at) {
            const now = Date.now();
            const limitDate = new Date(this.env.pos.pos_session.start_at);
            limitDate.setDate(limitDate.getDate() + 1);
            if (limitDate.getTime() < now) {
                const info = await this.env.pos.getClosePosInfo();
                this.popup.add(ClosePosPopup, { info: info, keepBehind: true });
            }
        }
    },
});
