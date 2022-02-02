/** @odoo-module **/

const { Component, xml, onWillDestroy } = owl;

export class EffectContainer extends Component {
    setup() {
        this.effect = null;
        const listenerRef = this.props.bus.addEventListener("UPDATE", (ev) => {
            this.effect = ev.detail;
            this.render();
        });
        onWillDestroy(() => {
            this.props.bus.removeEventListener("UPDATE", listenerRef);
        });
    }
    removeEffect() {
        this.effect = null;
        this.render();
    }
}

EffectContainer.template = xml`
  <div class="o_effects_manager">
    <t t-if="effect">
        <t t-component="effect.Component" t-props="effect.props" t-key="effect.id" close="() => this.removeEffect()"/>
    </t>
  </div>`;
