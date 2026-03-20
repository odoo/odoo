import { Component } from "@odoo/owl";
import { AnimatedNumber } from "./animated_number";
import { useService } from "@web/core/utils/hooks";

export class ColumnProgress extends Component {
    static components = {
        AnimatedNumber,
    };
    static template = "web.ColumnProgress";
    static props = {
        aggregate: { type: Object },
        group: { type: Object },
        onBarClicked: { type: Function, optional: true },
        progressBar: { type: Object },
    };
    static defaultProps = {
        onBarClicked: () => {},
    };

    setup() {
        this.offlineService = useService("offline");
    }

    async onBarClick(bar) {
        await this.props.onBarClicked(bar);
    }
}
