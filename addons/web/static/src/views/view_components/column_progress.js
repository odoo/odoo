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
    };
}
