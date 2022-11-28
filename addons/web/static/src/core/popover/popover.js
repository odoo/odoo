/** @odoo-module **/

import { usePosition } from "../position_hook";

const { Component } = owl;

export class Popover extends Component {
    setup() {
        usePosition(this.props.target, {
            onPositioned: this.onPositioned.bind(this),
            position: this.props.position,
        });
    }
    onPositioned(el, { direction, variant }) {
        const position = `${direction[0]}${variant[0]}`;

        // reset all popover classes
        el.classList = [
            "o_popover popover mw-100 shadow-sm",
            `bs-popover-${direction}`,
            `o-popover--${position}`,
        ].join(" ");
        if (this.props.popoverClass) {
            el.classList.add(...this.props.popoverClass.split(" "));
        }

        // reset all arrow classes
        const arrowEl = el.firstElementChild;
        arrowEl.className = "arrow";
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
