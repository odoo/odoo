/** @odoo-module **/

import { Component, useRef } from "@odoo/owl";
import { useForwardRefToParent } from "../utils/hooks";
import { usePosition } from "@web/core/position_hook";
import { addClassesToElement } from "../utils/className";

export function nextId() {
    nextId.current = (nextId.current || 0) + 1;
    return nextId.current;
}

export class Popover extends Component {
    setup() {
        this.id = nextId();
        this.arrow = useRef("popoverArrow");

        useForwardRefToParent("ref");
        usePosition(this.props.target, {
            onPositioned: this.props.onPositioned || this.onPositioned.bind(this),
            position: this.props.position,
            popper: "ref",
            fixedPosition: this.props.fixedPosition,
        });
    }

    onPositioned(el, { direction, variant }) {
        const position = `${direction[0]}${variant[0]}`;

        el.setAttribute("data-popover-id", this.id);
        this.props.target.setAttribute("data-popover-for", this.id);

        // reset all popover classes
        el.classList = [];
        const directionMap = {
            top: "top",
            bottom: "bottom",
            left: "start",
            right: "end",
        };
        addClassesToElement(
            el,
            "o_popover popover mw-100 shadow",
            `bs-popover-${directionMap[direction]}`,
            `o-popover-${direction}`,
            `o-popover--${position}`,
            this.props.class
        );

        if (!this.props.enableArrow) {
            el.classList.add("o-popover-no-arrow");
            return;
        }

        if (!this.arrow.el) {
            return;
        }

        // reset all arrow classes
        this.arrow.el.className = "popover-arrow";
        switch (position) {
            case "tm": // top-middle
            case "bm": // bottom-middle
            case "tf": // top-fit
            case "bf": // bottom-fit
                this.arrow.el.classList.add("start-0", "end-0", "mx-auto");
                break;
            case "lm": // left-middle
            case "rm": // right-middle
            case "lf": // left-fit
            case "rf": // right-fit
                this.arrow.el.classList.add("top-0", "bottom-0", "my-auto");
                break;
            case "ts": // top-start
            case "bs": // bottom-start
                this.arrow.el.classList.add("end-auto");
                break;
            case "te": // top-end
            case "be": // bottom-end
                this.arrow.el.classList.add("start-auto");
                break;
            case "ls": // left-start
            case "rs": // right-start
                this.arrow.el.classList.add("bottom-auto");
                break;
            case "le": // left-end
            case "re": // right-end
                this.arrow.el.classList.add("top-auto");
                break;
        }
    }
}

Popover.template = "web.PopoverWowl";
Popover.defaultProps = {
    position: "bottom",
    class: "",
    role: "tooltip",
    enableArrow: true,
};
Popover.props = {
    ref: {
        type: Function,
        optional: true,
    },
    class: {
        optional: true,
        type: [String, Object],
    },
    role: {
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
    fixedPosition: {
        type: Boolean,
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
    enableArrow: {
        type: Boolean,
        optional: true,
    },
    slots: {
        type: Object,
        optional: true,
        shape: {
            default: { optional: true },
        },
    },
};
