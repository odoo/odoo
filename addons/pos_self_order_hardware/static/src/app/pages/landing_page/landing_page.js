import { patch } from "@web/core/utils/patch";
import { LandingPage } from "@pos_self_order/app/pages/landing_page/landing_page";

patch(LandingPage.prototype, {
    setup() {
        super.setup(...arguments);
        this.selfOrder.ledController.setDefault();
    },
});
