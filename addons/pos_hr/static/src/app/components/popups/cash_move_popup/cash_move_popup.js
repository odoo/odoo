import { CashMovePopup } from "@point_of_sale/app/components/popups/cash_move_popup/cash_move_popup";
import { patch } from "@web/core/utils/patch";

patch(CashMovePopup.prototype, {
    _prepareTryCashInOutPayload() {
        const result = super._prepareTryCashInOutPayload(...arguments);
        if (this.pos.config.module_pos_hr) {
            const employee_id = this.pos.getCashier().id;
            result[result.length - 1] = { ...result[result.length - 1], employee_id };
        }
        return result;
    },
    get partnerId() {
        return this.pos.config.module_pos_hr
            ? this.pos.cashier.work_contact_id?.id
            : super.partnerId;
    },
});
