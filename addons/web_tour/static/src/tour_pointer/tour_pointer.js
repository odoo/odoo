import { Component, useEffect, signal, t, useProps } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";

const oppositeSides = {
    left: "right",
    right: "left",
    top: "bottom",
    bottom: "top",
};

const correspondingAction = {
    left: "left",
    right: "right",
    top: "up",
    bottom: "down",
};

/**
 * @param {HTMLElement} element
 * @returns {HTMLElement | null}
 */
function getScrollParent(element) {
    if (!element) {
        return null;
    }
    // We cannot only rely on the fact that the element’s scrollHeight is
    // greater than its clientHeight. This might not be the case when a step
    // starts, and the scrollbar could appear later. For example, when clicking
    // on a "building block" in the "building block previews modal" during a
    // tour (in website edit mode). When the modal opens, not all "building
    // blocks" are loaded yet, and the scrollbar is not present initially.
    const overflowY = window.getComputedStyle(element).overflowY;
    const isScrollable =
        overflowY === "auto" ||
        overflowY === "scroll" ||
        (overflowY === "visible" && element === element.ownerDocument.scrollingElement);
    if (isScrollable) {
        return element;
    } else {
        return getScrollParent(element.parentNode);
    }
}

export class TourPointer {
    /**
     *
     * @param {Object} env
     * @param {Object} env.services has to contains overlay, popover, ui and orm services
     * @param {Boolean} env.autoScroll Will automatically scroll to the pointed element if outside the view
     */
    constructor(env) {
        this.env = env;
        this.anchor = document.createElement("div");
        this.anchor.classList.add("o_tour_anchor");
        document.body.append(this.anchor);
        this.removePopover = () => {};
        this.removeOverlay = () => {};
        this.removeScrollListener = () => {};
        this._trigger = false;
        this.lastTriggerPosition = false;
        this.currentAction = {};
        this.overlayProps = signal.Object({
            width: 0,
            height: 0,
            top: 0,
            left: 0,
        });
    }

    /**
     * The element currently pointed to.
     * @returns {HTMLElement|false}
     */
    get trigger() {
        return this._trigger;
    }

    set trigger(el) {
        this._trigger = el;
        this.removeScrollListener();
        if (el) {
            this.parentScroll = getScrollParent(el);
            const onScroll = () => this._checkOutsideScreen();
            this.parentScroll.addEventListener("scroll", onScroll);
            this.removeScrollListener = () =>
                this.parentScroll.removeEventListener("scroll", onScroll);
        }
    }

    /**
     * Where {@link trigger} currently is on the view.
     * @private
     * @returns {"out-top"|"out-bottom"|"out-left"|"out-right"|"in"}
     */
    get _triggerPosition() {
        const rect = this.trigger.getBoundingClientRect();
        const containerRect = getScrollParent(this.trigger).getBoundingClientRect();
        if (rect.bottom <= containerRect.top) {
            return "out-top";
        } else if (rect.top >= containerRect.bottom) {
            return "out-bottom";
        } else if (rect.right <= containerRect.left) {
            return "out-left";
        } else if (rect.left >= containerRect.right) {
            return "out-right";
        } else {
            return "in";
        }
    }

    /**
     * Point to a given HTML element or the part of the sreen
     * where to scroll to get to the element.
     *
     * @param {HTMLElement} el
     * @param {Object} action The action of an interactive tour steps
     */
    pointTo(el, action) {
        const { width, height, top, left } = el.getBoundingClientRect();
        this.overlayProps.set({
            width,
            height,
            top,
            left,
        });
        this.currentAction = action;

        if (el && this.trigger !== el && this.env.services.ui.activeElement().contains(el)) {
            this.trigger = el;
            this._remove();
            this.lastTriggerPosition = this._triggerPosition;

            if (this.lastTriggerPosition.startsWith("out-")) {
                if (this.env.autoScroll) {
                    this.trigger.scrollIntoView({ behavior: "smooth", block: "center" });
                } else {
                    this._openScroller();
                }
            } else {
                this._openPopover();
            }
        }
    }

    /**
     * Removes the pointer and forgets about the current trigger, so that a
     * later call to {@link pointTo}, even for the same element, is not a
     * no-op.
     */
    hide() {
        this._remove();
        this.trigger = false;
        this.lastTriggerPosition = false;
    }

    /**
     * Removes the pointer and its anchor element from the DOM. Call this
     * once the engine is no longer needed (e.g. when the tour finishes or
     * chains into another one).
     */
    destroy() {
        this.hide();
        this.anchor.remove();
    }

    /** @private */
    _openScroller() {
        const position = this.lastTriggerPosition.split("-")[1];
        const direction = oppositeSides[position];
        this._setAnchorPosition(direction);

        this.removePopover = this.env.services.popover.add(
            this.anchor,
            TourPointerContent,
            {
                content: _t("Scroll %s to reach the next step.", correspondingAction[position]),
                onClick: () => this.trigger.scrollIntoView({ behavior: "smooth", block: "center" }),
                hideButton: true,
                cursor: "pointer",
            },
            {
                closeOnClickAway: false,
                popoverClass: "m-3 o_tour_scroller",
                position: direction,
                setActiveElement: false,
                sequence: 1100, // sequence based on bootstrap z-index values.
            }
        );
    }

    /** @private */
    _openPopover() {
        const popoverProps = {
            onEnd: () => this._onStopClicked(),
            content: this.currentAction.content,
            hideButton: this.currentAction.hideButton,
        };

        this.removePopover = this.env.services.popover.add(
            this.trigger,
            TourPointerContent,
            popoverProps,
            {
                closeOnClickAway: false,
                popoverClass: "m-1 o_tour_pointer",
                position: this.currentAction.tooltipPosition,
                setActiveElement: false,
                sequence: 1100, // sequence based on bootstrap z-index values.
            }
        );

        this.removeOverlay = this.env.services.overlay.add(
            TourPointerOverlay,
            {
                boundingRect: this.overlayProps,
            },
            { sequence: 1100 } // sequence based on bootstrap z-index values.
        );
    }

    /** @private */
    _remove() {
        this.removePopover();
        this.removeOverlay();
    }

    /** @private */
    _setAnchorPosition(direction) {
        const parentRect = this.parentScroll.getBoundingClientRect();
        const triggerRect = this.trigger.getBoundingClientRect();
        switch (direction) {
            case "top":
                this.anchor.style.top = `${parentRect.top + parentRect.height}px`;
                this.anchor.style.left = `${triggerRect.left + triggerRect.width / 2}px`;
                break;
            case "bottom":
                this.anchor.style.top = `${parentRect.top}px`;
                this.anchor.style.left = `${triggerRect.left + triggerRect.width / 2}px`;
                break;
            case "left":
                this.anchor.style.top = `${triggerRect.top + triggerRect.height / 2}px`;
                this.anchor.style.left = `${parentRect.left + parentRect.width}px`;
                break;
            case "right":
                this.anchor.style.top = `${triggerRect.top + triggerRect.height / 2}px`;
                this.anchor.style.left = "0px";
                break;
        }
    }

    /** @private */
    async _onStopClicked() {
        await this.env.services.orm.call("res.users", "switch_tour_enabled", [false]);
        browser.location.reload();
    }

    /** @private */
    _checkOutsideScreen() {
        if (this.trigger && this._triggerPosition !== this.lastTriggerPosition) {
            this._remove();
            this.lastTriggerPosition = this._triggerPosition;
            if (this.lastTriggerPosition.startsWith("out-")) {
                this._openScroller();
            } else {
                this._openPopover();
            }
        }
    }
}

class TourPointerContent extends Component {
    props = useProps({
        onEnd: t.function().optional(() => {}),
        onClick: t.function().optional(() => {}),
        content: t.string(),
        hideButton: t.boolean().optional(),
        cursor: t.string().optional(),
    });

    static template = "web_tour.TourPointer.Content";
}

class TourPointerOverlay extends Component {
    props = useProps({
        boundingRect: t.function(),
    });
    static template = "web_tour.TourPointer.Overlay";

    tourOverlayRef = signal.ref();

    setup() {
        useEffect(() => {
            const tourOverlay = this.tourOverlayRef();
            if (tourOverlay) {
                tourOverlay.style.width = this.props.boundingRect().width + "px";
                tourOverlay.style.height = this.props.boundingRect().height + "px";
                tourOverlay.style.top = this.props.boundingRect().top + "px";
                tourOverlay.style.left = this.props.boundingRect().left + "px";
            }
        });
    }
}
