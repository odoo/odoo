/** @odoo-module **/

import { Component } from "@odoo/owl";
import { cn } from "@odx_owl/core/utils/cn";

class KbdBase extends Component {
    get classes() {
        return cn(this.baseClass, this.props.className);
    }
}

export class Kbd extends KbdBase {
    static template = "odx_owl.Kbd";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
        text: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        tag: "kbd",
        text: "",
    };
    baseClass = "odx-kbd";
}

export class KbdGroup extends KbdBase {
    static template = "odx_owl.KbdGroup";
    static props = Kbd.props;
    static defaultProps = {
        className: "",
        tag: "span",
        text: "",
    };
    baseClass = "odx-kbd-group";
}
