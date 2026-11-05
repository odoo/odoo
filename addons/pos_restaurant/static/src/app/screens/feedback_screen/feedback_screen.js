import { FeedbackScreen } from "@point_of_sale/app/screens/feedback_screen/feedback_screen";
import { patch } from "@web/core/utils/patch";

patch(FeedbackScreen.prototype, {
    isContinueSplitting() {
        const shouldContinue = super.isContinueSplitting(...arguments);
        return this.pos.config.module_pos_restaurant
            ? shouldContinue && !this.pos.selectedTable
            : shouldContinue;
    },
});
