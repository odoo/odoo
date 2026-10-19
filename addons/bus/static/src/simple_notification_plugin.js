import { onWillDestroy, Plugin, usePlugin } from "@odoo/owl";
import { BusPlugin } from "@bus/services/bus_plugin";
import { NotificationPlugin } from "@web/core/notifications/notification_plugin";
import { services } from "@web/core/services";

export class SimpleNotificationPlugin extends Plugin {
    bus = usePlugin(BusPlugin);
    notification = usePlugin(NotificationPlugin);

    setup() {
        const unsubscribe = this.bus.subscribe(
            "simple_notification",
            ({ message, sticky, title, type }) => {
                this.notification.add(message, { sticky, title, type });
            }
        );
        this.bus.start();

        onWillDestroy(unsubscribe);
    }
}

services.add(SimpleNotificationPlugin);
