import { patch } from "@web/core/utils/patch";
import { FeedbackScreen } from "@point_of_sale/app/screens/feedback_screen/feedback_screen";

patch(FeedbackScreen.prototype, {
    get canEditPayment() {
        return this.pos.is_french_country() ? false : super.canEditPayment;
    },
});
