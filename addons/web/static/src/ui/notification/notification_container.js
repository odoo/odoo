// @ts-check

/** @module @web/ui/notification/notification_container - Renders all active notifications with fade-out transitions */

import { Component, useState, xml } from "@odoo/owl";
import { Transition } from "@web/components/transition";

import { Notification } from "./notification";
/** Renders all active notifications with fade-out transitions. */
export class NotificationContainer extends Component {
    static props = {
        notifications: Object,
    };

    static template = xml`
        <div class="o_notification_manager">
            <t t-foreach="notifications" t-as="notification" t-key="notification">
                <Transition leaveDuration="0" immediate="true" name="'o_notification_fade'" t-slot-scope="transition">
                    <Notification t-props="notification_value.props" className="(notification_value.props.className || '') + ' ' + transition.className"/>
                </Transition>
            </t>
        </div>`;
    static components = { Notification, Transition };

    /** Make the notifications map reactive so the container re-renders on changes. */
    setup() {
        /** @type {Object<string, { props: Object }>} */
        this.notifications = useState(this.props.notifications);
    }
}
