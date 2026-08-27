import { patch } from "@web/core/utils/patch";
import { LandingPage } from "@pos_self_order/app/pages/landing_page/landing_page";

patch(LandingPage.prototype, {
    onWillStart() {
        super.onWillStart(...arguments);
        // A new customer starts here in kiosk (mobile: see SelfOrder.createNewOrder)
        if (this.selfOrder.config.self_ordering_mode === "kiosk") {
            this.selfOrder.deleteUnrelatedData();
        }
    },
});
