import { Component, t, useProps } from "@odoo/owl";

export class ClickbotOverlay extends Component {
    static template = "web.ClickbotOverlay";
    props = useProps({
        state: t.object(), // the ClickbotLauncher instance
    });

    get stats() {
        const runState = this.props.state.state;
        return runState.testingOffline ? runState.offlineStats : runState.onlineStats;
    }
}
