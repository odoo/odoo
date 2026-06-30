import { Component } from "@odoo/owl";

export class ClickbotOverlay extends Component {
    static template = "web.ClickbotOverlay";
    static props = {
        state: Object, // the ClickbotLauncher instance
    };

    get stats() {
        const runState = this.props.state.state;
        return runState.testingOffline ? runState.offlineStats : runState.onlineStats;
    }
}
