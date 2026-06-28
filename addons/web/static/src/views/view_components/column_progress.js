import { Component, props, t } from "@odoo/owl";
import { AnimatedNumber } from "./animated_number";
import { useService } from "@web/core/utils/hooks";

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
        this.offlineService = useService("offline");
    }

    async onBarClick(bar) {
        await this.props.onBarClicked(bar);
    }
}
