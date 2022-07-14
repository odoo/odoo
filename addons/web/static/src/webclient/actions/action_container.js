/** @odoo-module **/

import { ActionDialog } from "./action_dialog";

const { Component, xml, onWillDestroy, useEffect } = owl;

// -----------------------------------------------------------------------------
// ActionContainer (Component)
// -----------------------------------------------------------------------------
export class ActionContainer extends Component {
    setup() {
        this.info = {};
        this.hasVisibleContent = false;
        this.nextInfo = null;
        useEffect(() => {
            this.hasVisibleContent = Boolean(this.info.Component);
            if (this.nextInfo) {
                this.setInfo(this.nextInfo);
            }
        })
        const onActionManagerUpdate = this.onActionManagerUpdate.bind(this);
        this.env.bus.addEventListener("ACTION_MANAGER:UPDATE", onActionManagerUpdate);
        onWillDestroy(() => {
            this.env.bus.removeEventListener("ACTION_MANAGER:UPDATE", onActionManagerUpdate);
        });
    }

    setInfo(info) {
        this.info = info;
        this.nextInfo = null;
        this.render();
    }

    async onActionManagerUpdate({ detail: info }) {
        if (this.hasVisibleContent && !this.info.Component && info.Component) {
            // if we have some content, but an update requested clearing the
            // screen, and we now request some content, then we wait for the
            // screen to be updated before rendering the new content
            this.nextInfo = info;
        } else {
            this.setInfo(info);
        }
    }
}

ActionContainer.components = { ActionDialog };
ActionContainer.template = xml`
    <t t-name="web.ActionContainer">
      <div class="o_action_manager">
        <t t-if="info.Component" t-component="info.Component" className="'o_action'" t-props="info.componentProps" t-key="info.id"/>
      </div>
    </t>`;
