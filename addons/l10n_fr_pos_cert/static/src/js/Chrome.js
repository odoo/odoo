import { Chrome } from "@point_of_sale/app/pos_app";
import { patch } from "@web/core/utils/patch";
import { ClosePosPopup } from "@point_of_sale/app/components/popups/closing_popup/closing_popup";
import { onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

patch(Chrome.prototype, {
    setup() {
        super.setup(...arguments);
        this.dialog = useService("dialog");
        onMounted(async () => {
            if (this.pos.is_french_country() && this.pos.session.start_at) {
                const now = Date.now();
                const limitDate = new Date(this.pos.session.start_at);
                limitDate.setDate(limitDate.getDate() + 1);
                if (limitDate.getTime() < now) {
                    const info = await this.pos.getClosePosInfo();
                    this.dialog.add(ClosePosPopup, info);
                }
            }
        });
    },
});
