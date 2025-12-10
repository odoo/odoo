import { FeedbackScreen } from "@point_of_sale/app/screens/feedback_screen/feedback_screen";
import { patch } from "@web/core/utils/patch";

patch(FeedbackScreen.prototype, {
    goNext() {
        if (this.pos.isContinueSplitting(this.currentOrder)) {
            this.pos.continueSplitting(this.currentOrder);
        } else {
            super.goNext();
        }
    },
});
