import { browser } from "@web/core/browser/browser";
import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';

export class PaymentFailedNotification extends Interaction {
    static selector = ".o_website_sale_checkout_container";
    setup() {
        // Add a notification service to send notification when there's a payment error
        const errorMessage = browser.sessionStorage.getItem("errorMessage");
        if (errorMessage) {
            this.notification = this.services.notification;
            this.notification.add(errorMessage, { type: "danger", sticky: true });
        }
        browser.sessionStorage.removeItem("errorMessage");
    }
}

registry
    .category('public.interactions')
    .add('website_sale.payment_failed_notification', PaymentFailedNotification);
