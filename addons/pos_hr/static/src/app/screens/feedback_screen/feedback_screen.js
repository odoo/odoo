import { patch } from "@web/core/utils/patch";
import { FeedbackScreen } from "@point_of_sale/app/screens/feedback_screen/feedback_screen";

patch(FeedbackScreen.prototype, {
    get canEditPayment() {
        return super.canEditPayment && (!this.pos.config.module_pos_hr || this.pos.employeeIsAdmin);
    },
});
