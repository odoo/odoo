import { ClosePosPopup } from "@point_of_sale/app/components/popups/closing_popup/closing_popup";
import { patch } from "@web/core/utils/patch";

patch(ClosePosPopup.prototype, {
    hasUserAuthority() {
        if (!this.pos.config.module_pos_hr) {
            return super.hasUserAuthority();
        }
        const cashier = this.pos.cashier;
        return (
            (cashier._role == "manager" && cashier._user_role == "admin") ||
            this.allowedDifference()
        );
    },
});
