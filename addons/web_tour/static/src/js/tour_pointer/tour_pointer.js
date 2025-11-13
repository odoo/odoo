import { Component, reactive, useEffect, useRef, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { browser } from "@web/core/browser/browser";
import { usePosition } from "@web/core/position/position_hook";
import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";
import { getScrollParent, isInPage } from "@web_tour/js/utils/tour_utils";

const oppositeSides = {
    left: "right",
    right: "left",
    top: "bottom",
    bottom: "top",
};

/**
 * @typedef TourPointerState
 * @property {HTMLElement} [trigger]
 * @property {string} [content]
 * @property {boolean} [isZone]
 * @property {Direction} [position]
 */
export const pointerState = reactive({
    trigger: undefined,
    content: "",
    isZone: false,
    position: "bottom",
});

class TourPointerPopover extends Component {
    static props = {
        content: { type: String },
        close: { type: Function },
        onClick: { type: Function, optional: true },
        closeContent: { type: Function, optional: true },
        openContent: { type: Function, optional: true },
    };

    static template = "web_tour.TourPointer.Content";

    setup() {
        this.orm = useService("orm");
    }

    async onStopClicked() {
        await this.orm.call("res.users", "switch_tour_enabled", [false]);
        browser.location.reload();
    }
}

/**
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
                trigger: { type: HTMLElement, optional: true },
                content: { type: String, optional: true },
                isZone: { type: Boolean, optional: true },
                position: {
                    type: [
                        { value: "left" },
                        { value: "right" },
                        { value: "top" },
                        { value: "bottom" },
                    ],
                    optional: true,
                },
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
        this.closeTimeout = null;
        this.anchor = useRef("anchor");
        this.dropzone = useRef("dropzone");
        this.state = useState({
            showContent: false,
            direction: "bottom", //The side towards which the ball hangs
            triggerPosition: "unknow",
            scrollParent: undefined,
        });

        const anchorPositionOptions = {
            margin: -10,
        };

        Object.defineProperty(anchorPositionOptions, "position", {
            get: () => `${this.anchorPosition}-middle`,
            set: () => {},
            enumerable: true,
        });

        this.anchorUsePosition = usePosition(
            "anchor",
            () => this.scrollParent,
            anchorPositionOptions
        );

        /**
         * The pointer is the little ball that follows either the trigger if
         * it is visible on the screen or the anchor element otherwise.
         */

        const pointerPositionOptions = {
            onPositioned: (pointer, position) => {
                // When trigger position changes (in <=> out)
                const triggerPosition = this.triggerPosition;
                if (triggerPosition !== this.state.triggerPosition) {
                    this.popover.close();
                    this.state.triggerPosition = triggerPosition;
                }
                // Set direction of baball
                if (this.triggerPosition.startsWith("out-")) {
                    this.state.direction = this.pointerPosition;
                } else {
                    this.state.direction = position.direction;
                }
            },
        };

        Object.defineProperty(pointerPositionOptions, "position", {
            get: () => {
                if (this.props.pointerState.isZone) {
                    return `top-start`;
                }
                return `${this.pointerPosition}-middle`;
            },
            set: () => {},
            enumerable: true,
        });

        Object.defineProperty(pointerPositionOptions, "margin", {
            get: () => (this.props.pointerState.isZone ? 0 : 10),
            set: () => {},
            enumerable: true,
        });

        this.pointerUsePosition = usePosition(
            "pointer",
            () => {
                if (this.triggerPosition === "in") {
                    return this.trigger;
                } else {
                    return this.anchor.el;
                }
            },
            pointerPositionOptions
        );

        useEffect(
            () => {
                const trigger = this.trigger;
                if (!trigger) {
                    return;
                }

                this.popover.close();
                if (this.props.pointerState.isZone && this.dropzone.el) {
                    const triggerRect = this.trigger.getBoundingClientRect();
                    this.dropzone.el.style.width = `${triggerRect.width}px`;
                    this.dropzone.el.style.height = `${triggerRect.height}px`;
                }
                this.state.scrollParent = getScrollParent(trigger);
                this.anchorUsePosition.unlock();
                this.pointerUsePosition.unlock();

                const openContentHandler = () => this.openContent();
                const closeContentHandler = () => this.closeContent();

                trigger.addEventListener("mouseenter", openContentHandler);
                trigger.addEventListener("mouseleave", closeContentHandler);

                return () => {
                    trigger.removeEventListener("mouseenter", openContentHandler);
                    trigger.removeEventListener("mouseleave", closeContentHandler);
                };
            },
            () => [this.props.pointerState.trigger]
        );

        const popoverOptions = {
            onClose: () => {
                this.state.showContent = false;
            },
        };

        Object.defineProperty(popoverOptions, "position", {
            get: () => `${this.pointerPosition}-middle`,
            set: () => {},
            enumerable: true,
        });

        this.popover = usePopover(TourPointerPopover, popoverOptions);
    }

    get content() {
        const triggerPosition = this.triggerPosition;
        if (triggerPosition === "out-bottom") {
            return _t("Scroll down to reach the next step.");
        } else if (triggerPosition === "out-top") {
            return _t("Scroll up to reach the next step.");
        } else if (triggerPosition === "out-left") {
            return _t("Scroll left to reach the next step.");
        } else if (triggerPosition === "out-right") {
            return _t("Scroll right to reach the next step.");
        }
        return this.props.pointerState.content || "";
    }

    get isVisible() {
        return this.trigger && isInPage(this.trigger) && this.triggerPosition !== "unknow";
    }

    /**
     * Position where the anchor is anchored. Always at middle
     * @returns {"top"|"bottom"|"right"|"left"}
     */
    get anchorPosition() {
        if (this.triggerPosition.startsWith("out-")) {
            return this.triggerPosition.split("-").at(-1);
        }
        return "top";
    }

    /**
     * Position where the ball is anchored. Always at middle
     * @returns {"top"|"bottom"|"right"|"left"}
     */
    get pointerPosition() {
        if (this.triggerPosition.startsWith("out-")) {
            return oppositeSides[this.anchorPosition];
        }
        return this.props.pointerState.position || "bottom";
    }

    get scrollParent() {
        return this.state.scrollParent || document.body;
    }

    get trigger() {
        return this.props.pointerState.trigger;
    }

    /**
     * Where is the trigger in the scrollParent ?
     * @returns {"out-top"|"out-bottom"|"out-left"|"out-right"|"in"}
     */
    get triggerPosition() {
        if (!this.trigger || !this.scrollParent) {
            return "unknown";
        }
        const rect = this.trigger.getBoundingClientRect();
        const containerRect = this.scrollParent.getBoundingClientRect();
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

    openContent() {
        clearTimeout(this.closeTimeout);
        this.state.showContent = true;
        if (this.popover.isOpen) {
            return;
        }
        const triggerPosition = this.triggerPosition;
        let target = this.trigger;
        if (this.trigger && triggerPosition !== "in") {
            target = this.anchor.el;
        }
        this.popover.open(target, {
            content: this.content,
            closeContent: () => this.closeContent(),
            openContent: () => this.openContent(),
            onClick: () => {
                if (
                    this.triggerPosition === "in" &&
                    typeof this.props.pointerState.onClick === "function"
                ) {
                    this.props.pointerState.onClick();
                } else {
                    this.closeContent();
                    this.trigger.scrollIntoView({ behavior: "smooth", block: "nearest" });
                }
            },
        });
    }

    closeContent() {
        clearTimeout(this.closeTimeout);
        this.closeTimeout = setTimeout(() => {
            this.popover.close();
        }, 500);
    }
}
