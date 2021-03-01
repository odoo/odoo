/** @odoo-module **/

import { useService } from "../../core/hooks";

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
    this.debugMode = true;
    this.env.bus.on("RPC:REQUEST", this, this.requestCall);
    this.env.bus.on("RPC:RESPONSE", this, this.responseCall);
    this.uiService = useService("ui");
  }

  requestCall(rpcId) {
    if (this.state.count === 0) {
      this.state.show = true;
      this.blockUITimer = odoo.browser.setTimeout(this.uiService.block, 3000);
    }
    this.rpcIds.add(rpcId);
    this.state.count++;
  }

  responseCall(rpcId) {
    this.rpcIds.delete(rpcId);
    this.state.count = this.rpcIds.size;
    if (this.state.count === 0) {
      clearTimeout(this.blockUITimer);
      this.uiService.unblock();
      this.state.show = false;
    }
  }
}

LoadingIndicator.template = "wowl.LoadingIndicator";
