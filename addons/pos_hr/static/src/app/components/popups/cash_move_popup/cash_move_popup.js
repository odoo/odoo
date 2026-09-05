import { CashMovePopup } from "@point_of_sale/app/components/popups/cash_move_popup/cash_move_popup";
import { patch } from "@web/core/utils/patch";

patch(CashMovePopup.prototype, {
    _getCashInOutExtraParams() {
        const result = super._getCashInOutExtraParams();
        if (this.pos.config.module_pos_hr) {
            result.employee_id = this.pos.getCashier().id;
        }
        return result;
    },
    get partnerId() {
        return this.pos.config.module_pos_hr
            ? this.pos.cashier.work_contact_id?.id ?? super.partnerId
            : super.partnerId;
    },
});
