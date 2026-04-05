/** @odoo-module **/

import { Component } from "@odoo/owl";
import { cn } from "@odx_owl/core/utils/cn";

export class Spinner extends Component {
    static template = "odx_owl.Spinner";
    static props = {
        ariaLabel: { type: String, optional: true },
        className: { type: String, optional: true },
        size: { type: String, optional: true },
        title: { type: String, optional: true },
    };
    static defaultProps = {
        ariaLabel: "Loading",
        className: "",
        size: "default",
        title: "",
    };

    get classes() {
        return cn("odx-spinner", `odx-spinner--${this.props.size}`, this.props.className);
    }
}
