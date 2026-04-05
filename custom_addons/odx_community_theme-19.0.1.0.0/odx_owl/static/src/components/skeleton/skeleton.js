/** @odoo-module **/

import { Component } from "@odoo/owl";
import { cn } from "@odx_owl/core/utils/cn";

export class Skeleton extends Component {
    static template = "odx_owl.Skeleton";
    static props = {
        attrs: { type: Object, optional: true },
        className: { type: String, optional: true },
        tag: { type: String, optional: true },
    };
    static defaultProps = {
        attrs: {},
        className: "",
        tag: "div",
    };

    get classes() {
        return cn("odx-skeleton", this.props.className);
    }
}
