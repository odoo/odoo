/** @odoo-module **/
import { serviceRegistry } from "../webclient/service_registry";

const { EventBus } = owl.core;

export function convertRainBowMessage(message) {
  if (message instanceof jQuery) {
    return message.html();
  } else if (message instanceof Element) {
    return message.outerHTML;
  } else if (typeof message === "string") {
    return message;
  }
}

export const effectService = {
  dependencies: ["notification", "user"],
  deploy(env) {
    const bus = new EventBus();
    if (!env.services.user.showEffect) {
      return {
        create: (message, options) => {
          env.services.notification.create(message, { sticky: false });
        },
        bus,
      };
    }
    let effectId = 0;
    let effect = {};

    function create(message, options) {
      message = message || env._t("Well Done!");
      let type = "rainbow_man";
      if (options) {
        type = options.type || type;
      }
      if (type === "rainbow_man") {
        effect = Object.assign({ imgUrl: "/web/static/src/img/smile.svg" }, options, {
          id: ++effectId,
          message,
        });
        bus.trigger("UPDATE", effect);
      }
    }
    return { create, bus };
  },
};

serviceRegistry.add("effect", effectService);
