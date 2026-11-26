import { Component, usePlugin, t, useProps } from "@odoo/owl";
import { OfflinePlugin } from "@web/core/offline/offline_plugin";
import { AnimatedNumber } from "./animated_number";
import { localizeDigits } from "@web/core/l10n/numbering";

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

    localizeDigits = localizeDigits;

    props = useProps(columnProgressProps);

    setup() {
        this.offlinePlugin = usePlugin(OfflinePlugin);
    }

    async onBarClick(bar) {
        await this.props.onBarClicked(bar);
    }
}
