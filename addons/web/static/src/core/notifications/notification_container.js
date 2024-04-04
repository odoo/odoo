/** @odoo-module **/

import { Notification } from "./notification";
import { Transition } from "@web/core/transition";

import { Component, xml, useState } from "@odoo/owl";

export class NotificationContainer extends Component {
    setup() {
        this.notifications = useState(this.props.notifications);
    }
}

NotificationContainer.template = xml`
    <div class="o_notification_manager">
        <t t-foreach="notifications" t-as="notification" t-key="notification">
            <Transition leaveDuration="0" name="'o_notification_fade'" t-slot-scope="transition">
                <Notification t-props="notification_value.props" className="(notification_value.props.className || '') + ' ' + transition.className"/>
            </Transition>
        </t>
    </div>`;
NotificationContainer.components = { Notification, Transition };
