import { xml } from "@odoo/owl";
import { NotificationContainer } from "@web/core/notifications/notification_container";
import { notificationService } from "@web/core/notifications/notification_service";
import { registry } from "@web/core/registry";
import { CartNotification } from "@website_sale/js/notification/cart_notification/cart_notification";


export class CartNotificationContainer extends NotificationContainer {
    static components = {
        ...NotificationContainer.components,
        Notification: CartNotification,
    }
    static template = xml`
    <div class="position-fixed w-100 h-100 top-0 pe-none">
        <div class="d-flex flex-column container align-items-end">
            <t t-foreach="notifications" t-as="notification" t-key="notification">
                <Transition leaveDuration="0" name="'o_notification_fade'" t-slot-scope="transition">
                    <Notification t-props="notification_value.props" className="(notification_value.props.className || '') + ' ' + transition.className"/>
                </Transition>
            </t>
        </div>
    </div>`;
}

export const cartNotificationService = {
    ...notificationService,
    notificationContainer: CartNotificationContainer,
}

registry.category("services").add("cartNotificationService", cartNotificationService);
