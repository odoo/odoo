/** @odoo-module **/

import { Component, useEffect, useRef } from "@odoo/owl";
import { reposition } from "@web/core/position_hook";

/**
 * @typedef {import("../tour_service/tour_pointer_state").TourPointerState} TourPointerState
 *
 * @typedef TourPointerProps
 * @property {TourPointerState} pointerState
 * @property {boolean} bounce
 */

/** @extends {Component<TourPointerProps, any>} */
export class TourPointer extends Component {
    static props = {
        pointerState: {
            type: Object,
            shape: {
                anchor: { type: HTMLElement, optional: true },
                content: { type: String, optional: true },
                fixed: { type: Boolean, optional: true },
                isOpen: { type: Boolean, optional: true },
                isVisible: { type: Boolean, optional: true },
                onClick: { type: [Function, { value: null }], optional: true },
                onMouseEnter: { type: [Function, { value: null }], optional: true },
                onMouseLeave: { type: [Function, { value: null }], optional: true },
                position: {
                    type: [
                        { value: "left" },
                        { value: "right" },
                        { value: "top" },
                        { value: "bottom" },
                    ],
                    optional: true,
                },
                rev: { type: Number, optional: true },
            },
        },
        bounce: { type: Boolean, optional: true },
    };

    static defaultProps = {
        bounce: true,
    };

    static template = "web_tour.TourPointer";
    static width = 28; // in pixels
    static height = 28; // in pixels

    setup() {
        const rootRef = useRef("popper");
        /** @type {DOMREct | null} */
        let dimensions = null;
        let lastMeasuredContent = null;
        let lastOpenState = this.isOpen;
        let [anchorX, anchorY] = [0, 0];

        useEffect(
            () => {
                const { el } = rootRef;
                if (el) {
                    const hasContentChanged = lastMeasuredContent !== this.content;
                    const hasOpenStateChanged = lastOpenState !== this.isOpen;
                    lastOpenState = this.isOpen;

                    // Content changed: we must re-measure the dimensions of the text.
                    if (hasContentChanged) {
                        lastMeasuredContent = this.content;
                        el.style.removeProperty("width");
                        el.style.removeProperty("height");
                        dimensions = el.getBoundingClientRect();
                    }

                    // If the content or the "is open" state changed: we must apply
                    // new width and height properties
                    if (hasContentChanged || hasOpenStateChanged) {
                        const [width, height] = this.isOpen
                            ? [dimensions.width, dimensions.height]
                            : [this.constructor.width, this.constructor.height];
                        if (this.isOpen) {
                            el.style.removeProperty("transition");
                        } else {
                            // No transition if switching from open to closed
                            el.style.setProperty("transition", "none");
                        }
                        el.style.setProperty("width", `${width}px`);
                        el.style.setProperty("height", `${height}px`);
                    }

                    if (!this.isOpen) {
                        const { anchor } = this.props.pointerState;
                        if (anchor) {
                            const { x, y, width } = anchor.getBoundingClientRect();
                            const [lastAnchorX, lastAnchorY] = [anchorX, anchorY];
                            [anchorX, anchorY] = [x, y];
                            // Let's just say that the anchor is static if it moved less than 1px.
                            const delta = Math.sqrt(
                                Math.pow(x - lastAnchorX, 2) + Math.pow(y - lastAnchorY, 2)
                            );
                            if (delta < 1) {
                                return;
                            }
                            const wouldOverflow =
                                window.innerWidth - x - width / 2 < dimensions?.width;
                            el.classList.toggle("o_expand_left", wouldOverflow);
                            reposition(anchor, el, null, {
                                position: this.position,
                                margin: 6,
                                onPositioned: (popper, position) => {
                                    const popperRect = popper.getBoundingClientRect();
                                    const { top, left, direction } = position;
                                    if (direction === "top") {
                                        popper.style.bottom = `${
                                            window.innerHeight - top - popperRect.height
                                        }px`;
                                        popper.style.removeProperty("top");
                                    } else {
                                        popper.style.top = `${top}px`;
                                    }
                                    if (direction === "left") {
                                        popper.style.right = `${
                                            window.innerWidth - left - popperRect.width
                                        }px`;
                                        popper.style.removeProperty("left");
                                    } else {
                                        popper.style.left = `${left}px`;
                                    }
                                },
                            });
                        }
                    }
                } else {
                    lastMeasuredContent = null;
                    lastOpenState = false;
                    dimensions = null;
                }
            },
            () => [this.props.pointerState.rev]
        );
    }

    get content() {
        return this.props.pointerState.content || "";
    }

    get isOpen() {
        return this.props.pointerState.isOpen;
    }

    get position() {
        return this.props.pointerState.position || "top";
    }
}
