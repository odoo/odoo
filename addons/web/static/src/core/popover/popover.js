/** @odoo-module **/

import { Component } from "@odoo/owl";
import { useForwardRefToParent } from "../utils/hooks";
import { usePosition } from "@web/core/position_hook";

export class Popover extends Component {
    setup() {
        useForwardRefToParent("ref");
        usePosition(this.props.target, {
            onPositioned: this.props.onPositioned || this.onPositioned.bind(this),
            position: this.props.position,
            popper: "ref",
        });
    }
    onPositioned(el, { direction, variant }) {
        const position = `${direction[0]}${variant[0]}`;

        // reset all popover classes
        const directionMap = {
            top: "top",
            bottom: "bottom",
            left: "start",
            right: "end",
        };
        el.classList = [
            "o_popover popover mw-100",
            `bs-popover-${directionMap[direction]}`,
            `o-popover-${direction}`,
            `o-popover--${position}`,
        ].join(" ");
        if (this.props.class) {
            el.classList.add(...this.props.class.split(" "));
        }

        // reset all arrow classes
        const arrowEl = el.querySelector(".popover-arrow");
        arrowEl.className = "popover-arrow";
        switch (position) {
            case "tm": // top-middle
            case "bm": // bottom-middle
            case "tf": // top-fit
            case "bf": // bottom-fit
                arrowEl.classList.add("start-0", "end-0", "mx-auto");
                break;
            case "lm": // left-middle
            case "rm": // right-middle
            case "lf": // left-fit
            case "rf": // right-fit
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
    class: "",
};
Popover.props = {
    ref: {
        type: Function,
        optional: true,
    },
    class: {
        optional: true,
        type: String,
    },
    position: {
        type: String,
        validate: (p) => {
            const [d, v = "middle"] = p.split("-");
            return (
                ["top", "bottom", "left", "right"].includes(d) &&
                ["start", "middle", "end", "fit"].includes(v)
            );
        },
        optional: true,
    },
    onPositioned: {
        type: Function,
        optional: true,
    },
    target: {
        validate: (target) => {
            // target may be inside an iframe, so get the Element constructor
            // to test against from its owner document's default view
            const Element = target?.ownerDocument?.defaultView.Element;
            return Boolean(Element) && target instanceof Element;
        },
    },
    slots: {
        type: Object,
        optional: true,
        shape: {
            default: { optional: true },
        },
    },
};
