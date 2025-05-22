import { Component } from "@odoo/owl";
import { AnimatedNumber } from "./animated_number";
import { _t } from "@web/core/l10n/translation";

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

    async onBarClick(bar) {
        await this.props.onBarClicked(bar);
    }

    get invalidAggregateTooltip() {
        return _t("Different currencies cannot be aggregated");
    }
}
