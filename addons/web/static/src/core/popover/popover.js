/** @odoo-module **/

import { usePosition } from "../position_hook";

const { Component } = owl;

export class Popover extends Component {
    setup() {
        usePosition(this.props.target, "popper", {
            margin: 16,
            onPositioned: this.onPositioned,
            position: this.props.position,
        });
    }
    onPositioned(el, { direction, variant }) {
        const position = `${direction[0]}${variant[0]}`;
        el.classList.add(`o-popper-position--${position}`);
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
        optional: true,
    },
    target: HTMLElement,
    slots: {
        type: Object,
        optional: true,
        shape: {
            default: { optional: true },
        },
    },
};
