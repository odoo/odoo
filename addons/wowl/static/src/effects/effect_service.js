/** @odoo-module **/
import { useService } from "../core/hooks";
import { serviceRegistry } from "../services/service_registry";
import { mainComponentRegistry } from "../webclient/main_component_registry";
import { RainbowMan } from "./rainbow_man";

const { Component, core, tags } = owl;
const { EventBus } = core;

export class EffectsContainer extends Component {
  setup() {
    this.rainbowProps = {};
    const { bus } = useService("effect");
    bus.on("UPDATE", this, effect => {
      this.rainbowProps = effect;
      this.render();
    });

  }
  closeRainbowMan() {
    this.rainbowProps = {};
    this.render();
  }
}

mainComponentRegistry.add("EffectsContainer", EffectsContainer);


EffectsContainer.template = tags.xml`
    <div class="o_effects_manager">
      <RainbowMan t-if="rainbowProps.id" t-props="rainbowProps" t-key="rainbowProps.id" t-on-close-rainbowman="closeRainbowMan"/>
    </div>`;
EffectsContainer.components = { RainbowMan };

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
    const bus = new EventBus();
    if (!env.services.user.showEffect) {
      return {
        create: (message, options) => {
          env.services.notification.create(message, { sticky: false });
        },
        bus
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