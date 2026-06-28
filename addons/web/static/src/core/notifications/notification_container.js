import { Notification } from "./notification";
import { Transition } from "@web/core/transition";

import { Component, xml, proxy } from "@odoo/owl";

export class NotificationContainer extends Component {
    static props = {
        notifications: Object,
    };

    static template = xml`
        <div class="o_notification_manager">
            <t t-foreach="this.notifications" t-as="notification" t-key="notification">
                <Transition leaveDuration="0" immediate="true" name="'o_notification_fade'" t-slot-scope="transition">
                    <Notification t-props="notification_value.props" className="(notification_value.props.className || '') + ' ' + transition.className"/>
                </Transition>
            </t>
        </div>`;
    static components = { Notification, Transition };

    setup() {
        this.notifications = proxy(this.props.notifications);
    }
}
