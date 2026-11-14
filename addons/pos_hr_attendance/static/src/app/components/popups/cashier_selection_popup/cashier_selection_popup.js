import { patch } from "@web/core/utils/patch";
import { CashierSelectionPopup } from "@pos_hr/app/components/popups/cashier_selection_popup/cashier_selection_popup";

patch(CashierSelectionPopup.prototype, {
    setup() {
        super.setup(...arguments);
        this.pos.refreshAttendanceStates();
    },
});
