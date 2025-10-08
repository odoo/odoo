import { NotificationContainer } from "@web/core/notifications/notification_container";
import { CartNotification } from "@website_sale/js/cart_notification/cart_notification/cart_notification";

export class CartNotificationContainer extends NotificationContainer {
    static components = { ...NotificationContainer.components, Notification: CartNotification }
    static template = 'website_sale.CartNotificationContainer';
}
