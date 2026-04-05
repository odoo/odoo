/** @odoo-module **/

import { Component } from "@odoo/owl";
import { cn } from "@odx_owl/core/utils/cn";

export class Separator extends Component {
    static template = "odx_owl.Separator";
    static props = {
        className: { type: String, optional: true },
        decorative: { type: Boolean, optional: true },
        orientation: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        decorative: true,
        orientation: "horizontal",
    };

    get classes() {
        return cn(
            "odx-separator",
            {
                "odx-separator--vertical": this.props.orientation === "vertical",
                "odx-separator--horizontal": this.props.orientation !== "vertical",
            },
            this.props.className
        );
    }
}
