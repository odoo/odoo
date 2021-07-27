/** @odoo-module **/

import { ActionDialog } from "./action_dialog";

const { Component, tags } = owl;

// -----------------------------------------------------------------------------
// ActionContainer (Component)
// -----------------------------------------------------------------------------
export class ActionContainer extends Component {
    setup() {
        this.info = {};
        this.info_preload = {};
        this.env.bus.on("ACTION_MANAGER:UPDATE", this, (info) => {
            if (info.preload) {
                this.info_preload = info;
            } else {
                this.info = info;
            }
            this.render();
        });
    }

    destroy() {
        this.env.bus.off("ACTION_MANAGER:UPDATE", this);
        super.destroy();
    }
}
ActionContainer.components = { ActionDialog };
ActionContainer.template = tags.xml`
    <t t-name="web.ActionContainer">
      <div class="o_action_manager_preload" style="display:none">
        <t t-if="info_preload.Component" t-component="info_preload.Component" t-props="info_preload.componentProps" t-key="info_preload.id"/>
      </div>
      <div class="o_action_manager">
        <t t-if="info.Component" t-component="info.Component" t-props="info.componentProps" t-key="info.id"/>
      </div>
    </t>`;
