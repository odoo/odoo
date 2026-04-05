/** @odoo-module **/

import { Component } from "@odoo/owl";
import { cn } from "@odx_owl/core/utils/cn";

export class AspectRatio extends Component {
    static template = "odx_owl.AspectRatio";
    static props = {
        className: { type: String, optional: true },
        ratio: { type: Number, optional: true },
        slots: { type: Object, optional: true },
    };
    static defaultProps = {
        className: "",
        ratio: 16 / 9,
    };

    get classes() {
        return cn("odx-aspect-ratio", this.props.className);
    }

    get paddingStyle() {
        const ratio = this.props.ratio > 0 ? this.props.ratio : 16 / 9;
        return `padding-bottom: ${(100 / ratio).toFixed(4)}%;`;
    }
}
