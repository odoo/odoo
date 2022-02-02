/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const { Component, useState } = owl;

/**
 * Loading Indicator
 *
 * When the user performs an action, it is good to give him some feedback that
 * something is currently happening.  The purpose of the Loading Indicator is to
 * display a small rectangle on the bottom right of the screen with just the
 * text 'Loading' and the number of currently running rpcs.
 *
 * After a delay of 3s, if a rpc is still not completed, we also block the UI.
 */
export class LoadingIndicator extends Component {
    setup() {
        this.state = useState({
            count: 0,
            show: false,
        });
        this.rpcIds = new Set();
        this.env.bus.addEventListener("RPC:REQUEST", this.requestCall.bind(this));
        this.env.bus.addEventListener("RPC:RESPONSE", this.responseCall.bind(this));
        this.uiService = useService("ui");
    }

    requestCall({ detail: rpcId }) {
        if (this.state.count === 0) {
            this.state.show = true;
            this.blockUITimer = browser.setTimeout(() => {
                this.shouldUnblock = true;
                this.uiService.block();
            }, 3000);
        }
        this.rpcIds.add(rpcId);
        this.state.count++;
    }

    responseCall({ detail: rpcId }) {
        this.rpcIds.delete(rpcId);
        this.state.count = this.rpcIds.size;
        if (this.state.count === 0) {
            if (this.shouldUnblock) {
                this.uiService.unblock();
                this.shouldUnblock = false;
            } else {
                browser.clearTimeout(this.blockUITimer);
            }
            this.state.show = false;
        }
    }
}

LoadingIndicator.template = "web.LoadingIndicator";

registry.category("main_components").add("LoadingIndicator", {
    Component: LoadingIndicator,
});
