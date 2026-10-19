import { patch } from "@web/core/utils/patch";
import { PaymentStatus } from "@payment/interactions/payment_status";

patch(PaymentStatus.prototype, {
    setup() {
        super.setup();
        this.dwellStart = Date.now();
    },
    redirectToLandingPage(landingRoute) {
        const wait = Math.max(
            0,
            (parseInt(this.el.dataset.minDwell) || 0) - (Date.now() - this.dwellStart)
        );
        if (wait) {
            this.waitForTimeout(() => this.redirectToLandingPage(landingRoute), wait);
            return;
        }
        super.redirectToLandingPage(landingRoute);
    },
});
