/** @odoo-module **/

import { serviceRegistry } from "../services/service_registry";

const { EventBus } = owl.core;

const AUTOCLOSE_DELAY = 4000;

export const notificationService = {
  name: "notification",
  deploy(env) {
    let notifId = 0;
    let notifications = [];
    const bus = new EventBus();

    function close(id) {
      const index = notifications.findIndex((n) => n.id === id);
      if (index > -1) {
        notifications.splice(index, 1);
        bus.trigger("UPDATE", notifications);
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
      bus.trigger("UPDATE", notifications);
      if (!sticky) {
        odoo.browser.setTimeout(() => close(notif.id), AUTOCLOSE_DELAY);
      }
      return notif.id;
    }
    return { close, create, bus };
  },
};

serviceRegistry.add("notification", notificationService);