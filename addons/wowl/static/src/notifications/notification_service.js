/** @odoo-module **/

import { useService } from "../core/hooks";
import { Notification as NotificationComponent } from "./notification";

const { Component, core, tags } = owl;
const { EventBus } = core;

const AUTOCLOSE_DELAY = 4000;

class NotificationManager extends Component {
  setup() {
    this.notifications = [];
    useService("notifications")
  }
}
NotificationManager.template = tags.xml`
    <div class="o_notification_manager">
        <t t-foreach="notifications" t-as="notification" t-key="notification.id">
            <NotificationComponent t-props="notification" t-transition="o_notification_fade"/>
        </t>
    </div>`;
NotificationManager.components = { NotificationComponent };

export const notificationService = {
  name: "notifications",
  deploy(env) {
    let notifId = 0;
    let notifications = [];
    const bus = new EventBus();
    class ReactiveNotificationManager extends NotificationManager {
      constructor() {
        super(...arguments);
        bus.on("UPDATE", this, () => {
          this.notifications = notifications;
          this.render();
        });
      }
    }

    odoo.mainComponentRegistry.add("NotificationManager", ReactiveNotificationManager);
    function close(id) {
      const index = notifications.findIndex((n) => n.id === id);
      if (index > -1) {
        notifications.splice(index, 1);
        bus.trigger("UPDATE");
      }
    }
    function create(message, options) {
      const notif = Object.assign({}, options, {
        id: ++notifId,
        message,
      });
      const sticky = notif.sticky;
      delete notif.sticky;
      notifications.push(notif);
      bus.trigger("UPDATE");
      if (!sticky) {
        odoo.browser.setTimeout(() => close(notif.id), AUTOCLOSE_DELAY);
      }
      return notif.id;
    }
    return { close, create };
  },
};
