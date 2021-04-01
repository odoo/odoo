/** @odoo-module **/
import { useService } from "../core/hooks";
import { mainComponentRegistry } from "../webclient/main_component_registry";
import { RainbowMan } from "./rainbow_man";

const { Component, tags } = owl;

export class EffectContainer extends Component {
  setup() {
    this.rainbowProps = {};
    const { bus } = useService("effect");
    bus.on("UPDATE", this, (effect) => {
      this.rainbowProps = effect;
      this.render();
    });
  }
  closeRainbowMan() {
    this.rainbowProps = {};
    this.render();
  }
}

EffectContainer.template = tags.xml`
  <div class="o_effects_manager">
    <RainbowMan t-if="rainbowProps.id" t-props="rainbowProps" t-key="rainbowProps.id" t-on-close-rainbowman="closeRainbowMan"/>
  </div>`;
EffectContainer.components = { RainbowMan };

mainComponentRegistry.add("EffectContainer", EffectContainer);
