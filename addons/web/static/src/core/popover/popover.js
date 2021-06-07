/** @odoo-module **/

import { debounce, throttle } from "../utils/timing";

const { Component } = owl;
const { useExternalListener, useRef } = owl.hooks;

export class Popover extends Component {
    setup() {
        this.popoverRef = useRef("popover");

        useExternalListener(document, "scroll", throttle(this.compute, 50), { capture: true });
        useExternalListener(window, "resize", debounce(this.compute, 250));
    }

    mounted() {
        this.compute();
    }
    patched() {
        this.compute();
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Computes the popover according to its props. This method will try to
     * position the popover as requested (according to the `position` props).
     * If the requested position does not fit the viewport, other positions will
     * be tried in a clockwise order starting a the requested position
     * (e.g. starting from left: top, right, bottom). If no position is found
     * that fits the viewport, "bottom" is used.
     *
     * @private
     */
    compute() {
        const positioningData = this.constructor.computePositioningData(
            this.popoverRef.el,
            this.props.target
        );

        const ORDERED_POSITIONS = ["top", "bottom", "left", "right"];
        // copy the default ordered position to avoid updating them in place
        const positionIndex = ORDERED_POSITIONS.indexOf(this.props.position);
        // check if the requested position fits the viewport; if not,
        // try all other positions and find one that does
        const position = ORDERED_POSITIONS.slice(positionIndex)
            .concat(ORDERED_POSITIONS.slice(0, positionIndex))
            .map((pos) => positioningData[pos])
            .find((pos) => {
                this.popoverRef.el.style.top = `${pos.top}px`;
                this.popoverRef.el.style.left = `${pos.left}px`;
                const rect = this.popoverRef.el.getBoundingClientRect();
                const html = document.documentElement;
                return (
                    rect.top >= 0 &&
                    rect.left >= 0 &&
                    rect.bottom <= (window.innerHeight || html.clientHeight) &&
                    rect.right <= (window.innerWidth || html.clientWidth)
                );
            });

        // remove all existing positioning classes
        for (const pos of ORDERED_POSITIONS) {
            this.popoverRef.el.classList.remove(`o_popover_${pos}`);
        }

        if (position) {
            // apply the preferred found position that fits the viewport
            this.popoverRef.el.classList.add(`o_popover_${position.name}`);
        } else {
            // use the given `position` props because no position fits
            this.popoverRef.el.style.top = `${positioningData[this.props.position].top}px`;
            this.popoverRef.el.style.left = `${positioningData[this.props.position].left}px`;
            this.popoverRef.el.classList.add(`o_popover_${this.props.position}`);
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
    },
    target: HTMLElement,
};

/**
 * Compute the expected positioning coordinates for each possible
 * positioning based on the target and popover sizes.
 * In particular the popover must not overflow the viewport in any
 * direction, it should actually stay at `margin` distance from the
 * border to look good.
 *
 * @param {HTMLElement} popoverElement The popover element
 * @param {HTMLElement} targetElement The target element, to which
 *  the popover will be visually "bound"
 * @param {number} [margin=16] Minimal accepted margin from the border
 *  of the viewport.
 * @returns {Object}
 */
Popover.computePositioningData = function (popoverElement, targetElement, margin = 16) {
    // set target position, possible position
    const boundingRectangle = targetElement.getBoundingClientRect();
    const targetTop = boundingRectangle.top;
    const targetLeft = boundingRectangle.left;
    const targetHeight = targetElement.offsetHeight;
    const targetWidth = targetElement.offsetWidth;
    const popoverHeight = popoverElement.offsetHeight;
    const popoverWidth = popoverElement.offsetWidth;
    const windowWidth = window.innerWidth || document.documentElement.clientWidth;
    const windowHeight = window.innerHeight || document.documentElement.clientHeight;
    const leftOffsetForVertical = Math.max(
        margin,
        Math.min(
            Math.round(targetLeft - (popoverWidth - targetWidth) / 2),
            windowWidth - popoverWidth - margin
        )
    );
    const topOffsetForHorizontal = Math.max(
        margin,
        Math.min(
            Math.round(targetTop - (popoverHeight - targetHeight) / 2),
            windowHeight - popoverHeight - margin
        )
    );
    return {
        top: {
            name: "top",
            top: Math.round(targetTop - popoverHeight),
            left: leftOffsetForVertical,
        },
        right: {
            name: "right",
            top: topOffsetForHorizontal,
            left: Math.round(targetLeft + targetWidth),
        },
        bottom: {
            name: "bottom",
            top: Math.round(targetTop + targetHeight),
            left: leftOffsetForVertical,
        },
        left: {
            name: "left",
            top: topOffsetForHorizontal,
            left: Math.round(targetLeft - popoverWidth),
        },
    };
};
