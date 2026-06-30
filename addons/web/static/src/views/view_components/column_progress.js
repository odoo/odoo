import { Component, plugin, props, t } from "@odoo/owl";
import { OfflinePlugin } from "@web/core/offline/offline_plugin";
import { AnimatedNumber } from "./animated_number";

export const columnProgressProps = {
    aggregate: t.object(),
    group: t.object(),
    onBarClicked: t.function().optional(() => () => {}),
    progressBar: t.object(),
};

export class ColumnProgress extends Component {
    static components = {
        AnimatedNumber,
    };
    static template = "web.ColumnProgress";
    props = props(columnProgressProps);

    setup() {
        this.offlinePlugin = plugin(OfflinePlugin);
    }

    async onBarClick(bar) {
        await this.props.onBarClicked(bar);
    }
}
