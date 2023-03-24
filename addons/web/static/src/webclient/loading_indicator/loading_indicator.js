/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Transition } from "@web/core/transition";

import { Component, onWillDestroy, useState } from "@odoo/owl";

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
        this.uiService = useService("ui");
        this.state = useState({
            count: 0,
            show: false,
        });
        this.rpcIds = new Set();
        this.shouldUnblock = false;
        this.startShowTimer = null;
        this.blockUITimer = null;
        this.env.bus.addEventListener("RPC:REQUEST", this.requestCall.bind(this));
        this.env.bus.addEventListener("RPC:RESPONSE", this.responseCall.bind(this));
        onWillDestroy(() => {
            this.env.bus.removeEventListener("RPC:REQUEST", this.requestCall.bind(this));
            this.env.bus.removeEventListener("RPC:RESPONSE", this.responseCall.bind(this));
        });
    }

    requestCall({ detail: rpcId }) {
        if (this.state.count === 0) {
            browser.clearTimeout(this.startShowTimer);
            this.startShowTimer = browser.setTimeout(() => {
                if (this.state.count) {
                    this.state.show = true;
                    this.blockUITimer = browser.setTimeout(() => {
                        this.shouldUnblock = true;
                        this.uiService.block();
                    }, 3000);
                }
            }, 250);
        }
        this.rpcIds.add(rpcId);
        this.state.count++;
    }

    responseCall({ detail: rpcId }) {
        this.rpcIds.delete(rpcId);
        this.state.count = this.rpcIds.size;
        if (this.state.count === 0) {
            browser.clearTimeout(this.startShowTimer);
            browser.clearTimeout(this.blockUITimer);
            this.state.show = false;
            if (this.shouldUnblock) {
                this.uiService.unblock();
                this.shouldUnblock = false;
            }
        }
    }
}

LoadingIndicator.template = "web.LoadingIndicator";
LoadingIndicator.components = { Transition };

registry.category("main_components").add("LoadingIndicator", {
    Component: LoadingIndicator,
});
