/** @odoo-module **/

import { usePosition } from "../position_hook";

const { Component } = owl;

export class Popover extends Component {
    setup() {
        usePosition(this.props.target, {
            onPositioned: this.props.onPositioned || this.onPositioned,
            position: this.props.position,
        });
    }
    onPositioned(el, { direction, variant }) {
        const position = `${direction[0]}${variant[0]}`;
        const directionMap = {
            top: "top",
            bottom: "bottom",
            left: "start",
            right: "end",
        };
        el.classList.add(
            `bs-popover-${directionMap[direction]}`,
            `o-popover-${direction}`,
            `o-popover--${position}`
        );
        const arrowEl = el.firstElementChild;
        switch (position) {
            case "tm": // top-middle
            case "bm": // bottom-middle
                arrowEl.classList.add("start-0", "end-0", "mx-auto");
                break;
            case "lm": // left-middle
            case "rm": // right-middle
                arrowEl.classList.add("top-0", "bottom-0", "my-auto");
                break;
            case "ts": // top-start
            case "bs": // bottom-start
                arrowEl.classList.add("end-auto");
                break;
            case "te": // top-end
            case "be": // bottom-end
                arrowEl.classList.add("start-auto");
                break;
            case "ls": // left-start
            case "rs": // right-start
                arrowEl.classList.add("bottom-auto");
                break;
            case "le": // left-end
            case "re": // right-end
                arrowEl.classList.add("top-auto");
                break;
        }
    }
}

Popover.template = "web.PopoverWowl";
Popover.defaultProps = {
    position: "bottom",
};
Popover.props = {
    id: {
        optional: true,
        type: Number,
    },
    popoverClass: {
        optional: true,
        type: String,
    },
    position: {
        type: String,
        validate: (p) => ["top", "bottom", "left", "right"].includes(p),
        optional: true,
    },
    onPositioned: {
        type: Function,
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
