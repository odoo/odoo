// @ts-check
/** @odoo-module native */

import { Component, onWillDestroy, xml } from "@odoo/owl";
import { makeLogger } from "@web/core/debug/debug_logger";
import { useLifecycleLog } from "@web/core/debug/logger_hooks";
import { AppEvent } from "@web/core/events";

const log = makeLogger("web.action.container");

export class ActionContainer extends Component {
    static props = {};
    static template = xml`
        <t t-name="web.ActionContainer">
          <div class="o_action_manager">
            <t t-if="this.info.Component" t-component="this.info.Component" className="'o_action'" t-props="this.info.componentProps" t-key="this.info.id"/>
          </div>
        </t>`;

    setup() {
        /** @type {Record<string, any>} */
        this.info = {};
        /** @param {CustomEvent} event */
        useLifecycleLog(log);
        this.onActionManagerUpdate = ({ detail: info }) => {
            log.pipeline("update", () => ({
                id: info.id,
                component: info.Component?.name,
                jsId: info.componentProps?.jsId,
            }));
            this.info = info;
            this.render();
        };
        this.env.bus.addEventListener(
            AppEvent.ACTION_MANAGER_UPDATE,
            this.onActionManagerUpdate,
        );
        onWillDestroy(() => {
            this.env.bus.removeEventListener(
                AppEvent.ACTION_MANAGER_UPDATE,
                this.onActionManagerUpdate,
            );
        });
    }
}
