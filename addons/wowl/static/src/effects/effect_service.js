/** @odoo-module **/
import { serviceRegistry } from "../services/service_registry";
import { RainbowMan } from "./rainbow_man";

const { Component, core, tags } = owl;
const { EventBus } = core;

class EffectsManager extends Component {
  constructor() {
    super(...arguments);
    this.rainbowProps = {};
  }
  closeRainbowMan() {}
}
EffectsManager.template = tags.xml`
    <div class="o_effects_manager">
      <RainbowMan t-if="rainbowProps.id" t-props="rainbowProps" t-key="rainbowProps.id" t-on-close-rainbowman="closeRainbowMan"/>
    </div>`;
EffectsManager.components = { RainbowMan };

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
  name: "effect",
  dependencies: ["notification", "user"],
  deploy(env) {
    if (!env.services.user.showEffect) {
      return {
        create: (message, options) => {
          env.services.notification.create(message, { sticky: false });
        },
      };
    }
    let effectId = 0;
    let effect = {};
    const bus = new EventBus();
    class ReactiveEffectsManager extends EffectsManager {
      constructor() {
        super(...arguments);
        bus.on("UPDATE", this, () => {
          this.rainbowProps = effect;
          this.render();
        });
      }
      closeRainbowMan() {
        close();
      }
    }
    odoo.mainComponentRegistry.add("EffectsManager", ReactiveEffectsManager);
    function close() {
      effect = {};
      bus.trigger("UPDATE");
    }
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
        bus.trigger("UPDATE");
      }
    }
    return { create };
  },
};

serviceRegistry.add("effect", effectService);