/** @odoo-module **/

import { serviceRegistry } from "../webclient/service_registry";

const { EventBus } = owl.core;

export const uiService = {
  name: "ui",
  deploy(env) {
    const bus = new EventBus();

    function block() {
      bus.trigger("BLOCK");
    }
    function unblock() {
      bus.trigger("UNBLOCK");
    }
    return { block, unblock, bus };
  },
};

serviceRegistry.add("ui", uiService);
