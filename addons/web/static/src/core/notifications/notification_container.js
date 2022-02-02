/** @odoo-module **/

import { Notification } from "./notification";

const { Component, xml } = owl;

export class NotificationContainer extends Component {
    setup() {
        // this works, but then this component cannot be unmounted, then
        // remounted. would need a destroyed hook different from willunmount
        this.props.bus.addEventListener("UPDATE", this.render.bind(this));
    }
}

NotificationContainer.template = xml`
    <div class="o_notification_manager">
        <t t-foreach="props.notifications" t-as="notification" t-key="notification.id">
            <Notification t-props="notification.props"/>
            <!-- NXOWL t-transition="o_notification_fade" -->
        </t>
    </div>`;
NotificationContainer.components = { Notification };
