import { registry } from "@web/core/registry";
import { StickBelowHeader } from "@website/interactions/sticky_below_header";

export class CartNotificationSticky extends StickBelowHeader {
    static selector = ".o_cart_notification_sticky";

    setup() {
        super.setup();
        this.defaultOffset = 0;
    }
}

registry
    .category("public.interactions")
    .add("website_sale.cart_notification_sticky", CartNotificationSticky);
