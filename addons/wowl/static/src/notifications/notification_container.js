/** @odoo-module **/

import { useService } from "../core/hooks";
import { mainComponentRegistry } from "../webclient/main_component_registry";
import { Notification as NotificationComponent } from "./notification";

const { Component, tags } = owl;

export class NotificationContainer extends Component {
  setup() {
    this.notifications = [];
    const { bus } = useService("notification");
    bus.on("UPDATE", this, (notifications) => {
      this.notifications = notifications;
      this.render();
    });
  }
}

NotificationContainer.template = tags.xml`
    <div class="o_notification_manager">
        <t t-foreach="notifications" t-as="notification" t-key="notification.id">
            <NotificationComponent t-props="notification" t-transition="o_notification_fade"/>
        </t>
    </div>`;
NotificationContainer.components = { NotificationComponent };

mainComponentRegistry.add("NotificationContainer", NotificationContainer);
