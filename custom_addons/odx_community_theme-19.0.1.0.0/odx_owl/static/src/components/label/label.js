/** @odoo-module **/

import { Component } from "@odoo/owl";
import { cn } from "@odx_owl/core/utils/cn";

export class Label extends Component {
    static template = "odx_owl.Label";
    static props = {
        className: { type: String, optional: true },
        forId: { type: String, optional: true },
        slots: { type: Object, optional: true },
        text: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        text: "",
    };

    get classes() {
        return cn("odx-label", this.props.className);
    }
}
