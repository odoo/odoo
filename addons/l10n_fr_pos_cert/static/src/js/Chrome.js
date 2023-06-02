/** @odoo-module */

import { Chrome } from "@point_of_sale/app/pos_app";
import { patch } from "@web/core/utils/patch";
import { ClosePosPopup } from "@point_of_sale/app/navbar/closing_popup/closing_popup";
import { onMounted } from "@odoo/owl";

patch(Chrome.prototype, "l10n_fr_pos_cert.Chrome", {
    setup() {
        this._super(...arguments);
        onMounted(async () => {
            const { globalState } = this.pos;
            if (globalState.is_french_country() && globalState.pos_session.start_at) {
                const now = Date.now();
                const limitDate = new Date(globalState.pos_session.start_at);
                limitDate.setDate(limitDate.getDate() + 1);
                if (limitDate.getTime() < now) {
                    const info = await globalState.getClosePosInfo();
                    this.popup.add(ClosePosPopup, { info });
                }
            }
        });
    },
});
