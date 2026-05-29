import { Component, useEffect, signal, types as t } from "@odoo/owl";
import { getScrollParent } from "@web_tour/js/utils/tour_utils";
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

export class TourInteractivePointer {
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
        this.currentTrigger = false;
        this.triggerPosition = false;
        this.currentAction = {};
        this.overlayProps = signal.Object({
            width: 0,
            height: 0,
            top: 0,
            left: 0,
        });
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
        })
        this.currentAction = action;

        if (el && this.currentTrigger !== el && this.env.services.ui.activeElement.contains(el)) {
            this.currentTrigger = el;
            this.triggerPosition = this.getTriggerPosition(el);

            this.parentScroll = getScrollParent(el);
            this.parentScroll.addEventListener("scroll", () => this.checkOutsideScreen());

            if (this.triggerPosition.startsWith("out-")) {
                if (this.env.autoScroll) {
                    this.currentTrigger.scrollIntoView({ behavior: "smooth", block: "center" });
                } else {
                    this.openScroller();
                }
            } else {
                if (this.currentTrigger) {
                    this.remove();
                }
                this.openPopover();
            }
        }
    }

    openScroller() {
        const position = this.triggerPosition.split("-")[1];
        const direction = oppositeSides[position];
        this.setAnchorPosition(direction);

        this.removePopover = this.env.services.popover.add(
            this.anchor,
            TourPointer,
            {
                content: _t("Scroll %s to reach the next step.", correspondingAction[position]),
                onClick: () =>
                    this.currentTrigger.scrollIntoView({ behavior: "smooth", block: "center" }),
                hideButton: true,
                cursor: "pointer",
            },
            {
                closeOnClickAway: false,
                popoverClass: "m-3 o_tour_scroller",
                position: direction,
                setActiveElement: false,
            }
        );
    }

    openPopover() {
        const popoverProps = {
            onEnd: () => this.onStopClicked(),
            content: this.currentAction.content,
            hideButton: this.currentAction.hideButton,
        };

        this.removePopover = this.env.services.popover.add(
            this.currentTrigger,
            TourPointer,
            popoverProps,
            {
                closeOnClickAway: false,
                popoverClass: "m-1 o_tour_pointer",
                position: this.currentAction.tooltipPosition,
                setActiveElement: false,
            }
        );

        this.removeOverlay = this.env.services.overlay.add(TourPointerOverlay, {
            boundingRect: this.overlayProps,
        });
    }

    remove() {
        this.removePopover();
        this.removeOverlay();
    }

    setAnchorPosition(direction) {
        const parentRect = this.parentScroll.getBoundingClientRect();
        const triggerRect = this.currentTrigger.getBoundingClientRect();
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

    async onStopClicked() {
        await this.env.services.orm.call("res.users", "switch_tour_enabled", [false]);
        browser.location.reload();
    }

    checkOutsideScreen() {
        if (
            this.currentTrigger &&
            this.getTriggerPosition(this.currentTrigger) != this.triggerPosition
        ) {
            this.remove();
            this.triggerPosition = this.getTriggerPosition(this.currentTrigger);
            if (this.getTriggerPosition(this.currentTrigger).startsWith("out-")) {
                this.openScroller();
            } else {
                this.openPopover();
            }
        }
    }

    /**
     * Get the position of the element on the view
     * @param {HTMLElement} el
     * @returns {"out-top"|"out-bottom"|"out-left"|"out-right"|"in"}
     */
    getTriggerPosition(el) {
        const rect = el.getBoundingClientRect();
        const containerRect = getScrollParent(el).getBoundingClientRect();
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
}

class TourPointer extends Component {
    static props = {
        onEnd: { type: Function, optional: true },
        onClick: { type: Function, optional: true },
        content: { type: String },
        close: { type: Function },
        hideButton: { type: Boolean, optional: true },
        cursor: { type: String, optional: true },
    };

    static defaultProps = {
        onClick: () => {},
        onEnd: () => {},
    };
    static template = "web_tour.TourInteractivePointer.Content";
}

class TourPointerOverlay extends Component {
    static props = {
        boundingRect: { type: Function }
    };
    static template = "web_tour.TourPointerOverlay";

    tourOverlayRef = signal(null, { type: t.ref(HTMLDivElement) });

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
