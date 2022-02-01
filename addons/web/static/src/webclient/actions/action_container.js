/** @odoo-module **/

import { ActionDialog } from "./action_dialog";

const { Component, xml, onWillDestroy } = owl;

// -----------------------------------------------------------------------------
// ActionContainer (Component)
// -----------------------------------------------------------------------------
export class ActionContainer extends Component {
    setup() {
        this.info = {};
        const updateInfo = ({ detail: info }) => {
            this.info = info;
            this.render();
        };

        this.env.bus.addEventListener("ACTION_MANAGER:UPDATE", updateInfo);
        onWillDestroy(() => {
            this.env.bus.removeEventListener("ACTION_MANAGER:UPDATE", updateInfo);
        });
    }
}
ActionContainer.components = { ActionDialog };
ActionContainer.template = xml`
    <t t-name="web.ActionContainer">
      <div class="o_action_manager">
        <t t-if="info.Component" t-component="info.Component" t-props="info.componentProps" t-key="info.id"/>
      </div>
    </t>`;
