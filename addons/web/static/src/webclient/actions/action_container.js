/** @odoo-module **/

import { ActionDialog } from "./action_dialog";

const { Component, tags } = owl;

// -----------------------------------------------------------------------------
// ActionContainer (Component)
// -----------------------------------------------------------------------------
export class ActionContainer extends Component {
    setup() {
        this.info = {};
        this.env.bus.on("ACTION_MANAGER:UPDATE", this, (info) => {
            this.info = info;
            this.render();
        });
    }

    __destroy() {
        this.env.bus.off("ACTION_MANAGER:UPDATE", this);
        super.__destroy();
    }
}
ActionContainer.components = { ActionDialog };
ActionContainer.template = tags.xml`
    <t t-name="web.ActionContainer">
      <div class="o_action_manager">
        <t t-if="info.Component" t-component="info.Component" t-props="info.componentProps" t-key="info.id"/>
      </div>
    </t>`;
