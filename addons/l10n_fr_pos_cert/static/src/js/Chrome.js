/** @odoo-module */

import { Chrome } from "@point_of_sale/app/pos_app";
import { patch } from "@web/core/utils/patch";
import { ClosePosPopup } from "@point_of_sale/app/navbar/closing_popup/closing_popup";
import { onMounted } from "@odoo/owl";

patch(Chrome.prototype, {
    setup() {
        super.setup(...arguments);
        onMounted(async () => {
            if (this.pos.is_french_country() && this.pos.pos_session.start_at) {
                const now = Date.now();
                const limitDate = new Date(this.pos.pos_session.start_at);
                limitDate.setDate(limitDate.getDate() + 1);
                if (limitDate.getTime() < now) {
                    const info = await this.pos.getClosePosInfo();
                    this.popup.add(ClosePosPopup, { ...info, keepBehind: true });
                }
            }
        });
    },
});
