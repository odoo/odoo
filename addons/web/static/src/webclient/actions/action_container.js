// @ts-check

/** @module @web/webclient/actions/action_container - Thin OWL wrapper rendering the current action's component inside the action manager div */

import { Component, onWillDestroy, xml } from "@odoo/owl";

// -----------------------------------------------------------------------------
// ActionContainer (Component)
// -----------------------------------------------------------------------------

/**
 * Thin OWL wrapper that listens for ACTION_MANAGER:UPDATE events on `env.bus`
 * and renders the current action's component inside the `.o_action_manager` div.
 */
export class ActionContainer extends Component {
    static props = {};
    static template = xml`
        <t t-name="web.ActionContainer">
          <div class="o_action_manager">
            <t t-if="info.Component" t-component="info.Component" className="'o_action'" t-props="info.componentProps" t-key="info.id"/>
          </div>
        </t>`;

    /** Subscribe to ACTION_MANAGER:UPDATE events and re-render on each update. */
    setup() {
        /** @type {Record<string, any>} */
        this.info = {};
        /** @param {CustomEvent} event */
        this.onActionManagerUpdate = ({ detail: info }) => {
            this.info = info;
            this.render();
        };
        this.env.bus.addEventListener(
            "ACTION_MANAGER:UPDATE",
            this.onActionManagerUpdate,
        );
        onWillDestroy(() => {
            this.env.bus.removeEventListener(
                "ACTION_MANAGER:UPDATE",
                this.onActionManagerUpdate,
            );
        });
    }
}
