import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class CouponToaster extends Interaction {
    static selector = ".coupon-message";

    start() {
        let options = {};
        const titleEl = this.el.querySelector(".coupon-message-title");
        const contentEl = this.el.querySelector(".coupon-message-content");
        let message = null;

        if (contentEl) {
            message = contentEl.innerHTML;
            if (titleEl) {
                Object.assign(options, { title: titleEl.innerHTML });
            }
        } else if (titleEl) {
            message = titleEl.innerHTML;
        }

        if (this.el.classList.contains("coupon-info-message")) {
            this.services.notification.add(message, Object.assign({ type: "success" }, options));
        } else if (this.el.classList.contains("coupon-error-message")) {
            this.services.notification.add(message, Object.assign({ type: "danger" }, options));
        } else if (this.el.classList.contains("coupon-warning-message")) {
            this.services.notification.add(message, Object.assign({ type: "warning" }, options));
        }
    }
}

registry
    .category("public.interactions")
    .add("website_sale_loyalty.coupon_toaster", CouponToaster);
