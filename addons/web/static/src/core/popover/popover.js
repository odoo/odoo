/** @odoo-module **/

import { usePosition } from "../position/position_hook";

const { Component } = owl;

export class Popover extends Component {
    setup() {
        usePosition(this.props.target, {
            margin: 16,
            position: this.props.position,
        });
    }
}

Popover.template = "web.PopoverWowl";
Popover.defaultProps = {
    position: "bottom",
};
Popover.props = {
    popoverClass: {
        optional: true,
        type: String,
    },
    position: {
        type: String,
        validate: (p) => ["top", "bottom", "left", "right"].includes(p),
    },
    target: HTMLElement,
};
