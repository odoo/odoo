/** @odoo-module **/

import { ActionDialog } from "./action_dialog";

const { Component, xml, onWillDestroy } = owl;

// -----------------------------------------------------------------------------
// ActionContainer (Component)
// -----------------------------------------------------------------------------
export class ActionContainer extends Component {
    setup() {
        this.info = {};
        this.onActionManagerUpdate = async ({ detail: info }) => {
            if (info.Component && !this.info.Component) {
                // we wait for one animation frame before rendering, so the new
                // rendering does not cancel the "empty" rendering, and we get
                // the chance to see the wonderful white screen
                await new Promise((resolve) => requestAnimationFrame(resolve));
            }
            this.info = info;
            this.render();
        };
        this.env.bus.addEventListener("ACTION_MANAGER:UPDATE", this.onActionManagerUpdate);
        onWillDestroy(() => {
            this.env.bus.removeEventListener("ACTION_MANAGER:UPDATE", this.onActionManagerUpdate);
        });
    }
}
ActionContainer.components = { ActionDialog };
ActionContainer.template = xml`
    <t t-name="web.ActionContainer">
      <div class="o_action_manager">
        <t t-if="info.Component" t-component="info.Component" className="'o_action'" t-props="info.componentProps" t-key="info.id"/>
      </div>
    </t>`;
