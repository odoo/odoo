/** @odoo-module **/

import { Component } from "@odoo/owl";
import { AnimatedNumber } from "./animated_number";

export class ColumnProgress extends Component {
    static components = {
        AnimatedNumber,
    };
    static template = "web.ColumnProgress";
    static props = {
        aggregate: { type: Object },
        group: { type: Object },
        onBarClicked: { type: Function, optional: true },
    };
    static defaultProps = {
        onBarClicked: () => {},
    };

    async onBarClick(progressBar) {
        await this.props.group.filterProgressValue(progressBar.value);
        this.props.onBarClicked();
    }
}
