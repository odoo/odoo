import { notificationService } from "@web/core/notifications/notification_service";
import { registry } from "@web/core/registry";
import { CartNotificationContainer } from "@website_sale/js/cart_notification/cart_notification_container/cart_notification_container";

export const cartNotificationService = {
    ...notificationService,
    notificationContainer: CartNotificationContainer,
}

registry.category("services").add("cartNotificationService", cartNotificationService);
