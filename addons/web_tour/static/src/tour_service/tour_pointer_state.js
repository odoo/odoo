/** @odoo-module **/

import { reactive } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { TourPointer } from "@web_tour/tour_pointer/tour_pointer";
import { getScrollParent } from "./tour_utils";

/**
 * @typedef {import("@web/core/position/position_hook").Direction} Direction
 *
 * @typedef {"in" | "out-below" | "out-above" | "unknown"} IntersectionPosition
 *
 * @typedef {ReturnType<createPointerState>["methods"]} TourPointerMethods
 *
 * @typedef TourPointerState
 * @property {HTMLElement} [anchor]
 * @property {string} [content]
 * @property {boolean} [isOpen]
 * @property {() => {}} [onClick]
 * @property {() => {}} [onMouseEnter]
 * @property {() => {}} [onMouseLeave]
 * @property {boolean} isVisible
 * @property {boolean} isZone
 * @property {Direction} position
 * @property {number} rev
 *
 * @typedef {import("./tour_service").TourStep} TourStep
 */

class Intersection {
    constructor() {
        /** @type {Element | null} */
        this.currentTarget = null;
        this.rootBounds = null;
        /** @type {IntersectionPosition} */
        this._targetPosition = "unknown";
        this._observer = new IntersectionObserver((observations) =>
            this._handleObservations(observations)
        );
    }

    /** @type {IntersectionObserverCallback} */
    _handleObservations(observations) {
        if (observations.length < 1) {
            return;
        }
        const observation = observations[observations.length - 1];
        this.rootBounds = observation.rootBounds;
        if (this.rootBounds && this.currentTarget) {
            if (observation.isIntersecting) {
                this._targetPosition = "in";
            } else {
                const scrollParentElement =
                    getScrollParent(this.currentTarget) || document.documentElement;
                const targetBounds = this.currentTarget.getBoundingClientRect();
                if (targetBounds.bottom > scrollParentElement.clientHeight) {
                    this._targetPosition = "out-below";
                } else if (targetBounds.top < 0) {
                    this._targetPosition = "out-above";
                } else if (targetBounds.left < 0) {
                    this._targetPosition = "out-left";
                } else if (targetBounds.right > scrollParentElement.clientWidth) {
                    this._targetPosition = "out-right";
                }
            }
        } else {
            this._targetPosition = "unknown";
        }
    }

    get targetPosition() {
        if (!this.rootBounds) {
            return this.currentTarget ? "in" : "unknown";
        } else {
            return this._targetPosition;
        }
    }

    /**
     * @param {Element} newTarget
     */
    setTarget(newTarget) {
        if (this.currentTarget !== newTarget) {
            if (this.currentTarget) {
                this._observer.unobserve(this.currentTarget);
            }
            if (newTarget) {
                this._observer.observe(newTarget);
            }
            this.currentTarget = newTarget;
        }
    }

    stop() {
        this._observer.disconnect();
    }
}

export function createPointerState() {
    /**
     * @param {Partial<TourPointerState>} newState
     */
    const setState = (newState) => {
        Object.assign(state, newState);
    };

    /**
     * @param {TourStep} step
     * @param {HTMLElement} [anchor]
     * @param {boolean} [isZone] will border de zone. e.g.: a dropzone
     */
    const pointTo = (anchor, step, isZone) => {
        intersection.setTarget(anchor);
        if (anchor) {
            let { tooltipPosition, content } = step;
            switch (intersection.targetPosition) {
                case "unknown": {
                    // Do nothing for unknown target position.
                    break;
                }
                case "in": {
                    if (document.body.contains(floatingAnchor)) {
                        floatingAnchor.remove();
                    }
                    setState({
                        anchor,
                        content,
                        isZone,
                        onClick: null,
                        position: tooltipPosition,
                        isVisible: true,
                    });
                    break;
                }
                default: {
                    const onClick = () => {
                        anchor.scrollIntoView({ behavior: "smooth", block: "nearest" });
                        hide();
                    };

                    const scrollParent = getScrollParent(anchor);
                    if (!scrollParent) {
                        setState({
                            anchor,
                            content,
                            isZone,
                            onClick: null,
                            position: tooltipPosition,
                            isVisible: true,
                        });
                        return;
                    }
                    let { x, y, width, height } = scrollParent.getBoundingClientRect();

                    // If the scrolling element is within an iframe the offsets
                    // must be computed taking into account the iframe.
                    const iframeEl = scrollParent.ownerDocument.defaultView.frameElement;
                    if (iframeEl) {
                        const iframeOffset = iframeEl.getBoundingClientRect();
                        x += iframeOffset.x;
                        y += iframeOffset.y;
                    }
                    if (intersection.targetPosition === "out-below") {
                        tooltipPosition = "top";
                        content = _t("Scroll down to reach the next step.");
                        floatingAnchor.style.top = `${y + height - TourPointer.height}px`;
                        floatingAnchor.style.left = `${x + width / 2}px`;
                    } else if (intersection.targetPosition === "out-above") {
                        tooltipPosition = "bottom";
                        content = _t("Scroll up to reach the next step.");
                        floatingAnchor.style.top = `${y + TourPointer.height}px`;
                        floatingAnchor.style.left = `${x + width / 2}px`;
                    }
                    if (intersection.targetPosition === "out-left") {
                        tooltipPosition = "right";
                        content = _t("Scroll left to reach the next step.");
                        floatingAnchor.style.top = `${y + height / 2}px`;
                        floatingAnchor.style.left = `${x + TourPointer.width}px`;
                    } else if (intersection.targetPosition === "out-right") {
                        tooltipPosition = "left";
                        content = _t("Scroll right to reach the next step.");
                        floatingAnchor.style.top = `${y + height / 2}px`;
                        floatingAnchor.style.left = `${x + width - TourPointer.width}px`;
                    }
                    if (!document.contains(floatingAnchor)) {
                        document.body.appendChild(floatingAnchor);
                    }
                    setState({
                        anchor: floatingAnchor,
                        content,
                        onClick,
                        position: tooltipPosition,
                        isZone,
                        isVisible: true,
                    });
                }
            }
        } else {
            hide();
        }
    };

    function hide() {
        setState({ content: "", isVisible: false, isOpen: false });
    }

    function showContent(isOpen) {
        setState({ isOpen });
    }

    function destroy() {
        intersection.stop();
        if (document.body.contains(floatingAnchor)) {
            floatingAnchor.remove();
        }
    }

    /** @type {TourPointerState} */
    const state = reactive({});
    const intersection = new Intersection();
    const floatingAnchor = document.createElement("div");
    floatingAnchor.className = "position-fixed";

    return { state, setState, showContent, pointTo, hide, destroy };
}
