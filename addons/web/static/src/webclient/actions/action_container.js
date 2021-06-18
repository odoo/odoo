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

    destroy() {
        this.env.bus.off("ACTION_MANAGER:UPDATE", this);
        super.destroy();
    }

    catchError() {
        this.info = {};
        this.render();
        // we trigger here the 'MENUS-APP-CHANGED' event to make sure the navbar
        // is properly displayed/updated.
        this.env.bus.trigger("MENUS:APP-CHANGED");

        // we do not rethrow the error here, because the controller component
        // already caught the error, and rejected the doAction promise. That
        // doAction promise will then trigger an unhandledRejection error, which
        // will be displayed by the error service (unless the promise is handled
        // by some caller code, but then in that case, it is its own responsibility
        // to handle the error properly.
    }
}
ActionContainer.components = { ActionDialog };
ActionContainer.template = tags.xml`
    <t t-name="web.ActionContainer">
      <div class="o_action_manager">
        <t t-if="info.Component" t-component="info.Component" t-props="info.componentProps" t-key="info.id"/>
      </div>
    </t>`;
