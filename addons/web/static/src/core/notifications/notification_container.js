import { Notification } from "./notification";
import { Transition } from "@web/core/transition";
import { registry } from "@web/core/registry";
import { Component, onWillDestroy, plugin, Plugin, xml } from "@odoo/owl";
import { NotificationPlugin } from "./notification_plugin";
import { services } from "@web/core/services";

export class NotificationContainer extends Component {
    notificationPlugin = plugin(NotificationPlugin);

    static template = xml`
        <div class="o_notification_manager">
            <t t-foreach="this.notificationPlugin.notifications.items()" t-as="notification" t-key="notification.id">
                <Transition leaveDuration="0" immediate="true" name="'o_notification_fade'" t-slot-scope="transition">
                    <Notification notification="notification_value.props" className="(notification_value.props.className || '') + ' ' + transition.className"/>
                </Transition>
            </t>
        </div>`;
    static components = { Notification, Transition };
}

export class NotificationManagerPlugin extends Plugin {
    setup() {
        registry.category("main_components").add(
            NotificationContainer.name,
            { Component: NotificationContainer },
            { sequence: 100 }
        );

        onWillDestroy(() => {
            registry.category("main_components").remove(NotificationContainer.name);
        });
    }
}

services.add(NotificationManagerPlugin);
