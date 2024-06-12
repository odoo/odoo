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
        progressBar: { type: Object },
    };
    static defaultProps = {
        onBarClicked: () => {},
    };

    async onBarClick(bar) {
        await this.props.onBarClicked(bar);
    }
}
