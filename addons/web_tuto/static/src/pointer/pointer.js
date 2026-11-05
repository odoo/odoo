import { Component, onPatched, proxy, signal } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { usePosition } from "@web/core/position/position_hook";
import { closestScrollableY } from "@web/core/utils/scrolling";
import { useDebounced } from "@web/core/utils/timing";
import { pointerState } from "@web_tuto/pointer/pointer_state";

const bootstrapSides = {
    bottom: "bottom",
    left: "start",
    right: "end",
    top: "top",
};

const oppositeSides = {
    bottom: "top",
    left: "right",
    right: "left",
    top: "bottom",
};

const outOfViewSides = {
    "out-bottom": "bottom",
    "out-left": "left",
    "out-right": "right",
    "out-top": "top",
};

/**
 * A ball following its trigger, with a bubble explaining what to do, open
 * while hovered or always (a hint, or the tips always shown). While the
 * trigger is out of view, the ball waits on the edge of its scroll parent.
 */
export class TutorialPointer extends Component {
    /** How long the bubble stays open after the mouse left, in milliseconds */
    static closeDelay = 300;
    /** The space between the ball and its trigger, in pixels */
    static margin = 10;
    static template = "web_tuto.TutorialPointer";

    bubbleRef = signal.ref();
    pointerRef = signal.ref();
    pointerState = pointerState;

    /**
     * Places the ball next to its trigger, or inside the edge of its scroll
     * parent (a negative margin) while the trigger is out of view
     */
    setup() {
        this.state = proxy({
            /** What was hovered, the bubble staying open while still pointed */
            hoveredContent: null,
            hoveredTrigger: null,
            /** The side of its trigger (or of the edge) the ball is on */
            side: "bottom",
            /** Whether the trigger was in view when the ball was last placed */
            triggerVisibility: "unknown",
        });
        const pointer = this;
        usePosition(
            this.pointerRef,
            () =>
                this._measureTriggerVisibility() === "in"
                    ? this._trigger
                    : closestScrollableY(this._trigger) || document.body,
            {
                get margin() {
                    const { margin } = pointer.constructor;
                    return pointer._measureTriggerVisibility() === "in"
                        ? margin
                        : -(pointer.pointerRef().offsetWidth + margin);
                },
                onPositioned: (pointerEl, { direction }) => {
                    const triggerVisibility = this._measureTriggerVisibility();
                    this.state.triggerVisibility = triggerVisibility;
                    this.state.side =
                        triggerVisibility === "in" ? direction : oppositeSides[direction];
                    this._keepBubbleInView();
                },
                get position() {
                    const triggerVisibility = pointer._measureTriggerVisibility();
                    const side =
                        outOfViewSides[triggerVisibility] || pointer.pointerState.side || "bottom";
                    return `${side}-middle`;
                },
                rememberPosition: false,
            }
        );
        onPatched(() => this._keepBubbleInView());
        this.closeContent = useDebounced(() => {
            this.state.hoveredTrigger = null;
            this.state.hoveredContent = null;
        }, this.constructor.closeDelay);
    }

    get bubbleSide() {
        return bootstrapSides[this.state.side];
    }

    /** Where to scroll while the trigger is out of view, the help otherwise */
    get content() {
        const scrollHints = {
            "out-bottom": _t("Scroll down to reach the next step."),
            "out-left": _t("Scroll left to reach the next step."),
            "out-right": _t("Scroll right to reach the next step."),
            "out-top": _t("Scroll up to reach the next step."),
        };
        return scrollHints[this.state.triggerVisibility] || this.pointerState.content || "";
    }

    get isVisible() {
        return Boolean(this._trigger?.isConnected);
    }

    onContentClick() {
        if (this.state.triggerVisibility !== "in") {
            this._trigger.scrollIntoView({ behavior: "smooth", block: "nearest" });
        }
    }

    onMouseEnter() {
        this.closeContent.cancel();
        this.state.hoveredTrigger = this._trigger;
        this.state.hoveredContent = this.pointerState.content;
    }

    onMouseLeave() {
        this.closeContent();
    }

    get showContent() {
        const { alwaysOpen, tipsShown } = this.pointerState;
        return (
            Boolean(alwaysOpen || tipsShown) ||
            (this.state.hoveredTrigger === this._trigger &&
                this.state.hoveredContent === this.pointerState.content)
        );
    }

    /**
     * Shifts the bubble so that it doesn't overflow the window
     * @private
     */
    _keepBubbleInView() {
        const bubble = this.bubbleRef();
        if (!bubble) {
            return;
        }
        bubble.style.removeProperty("--TutorialPointer__shift");
        if (!["top", "bottom"].includes(this.state.side)) {
            return;
        }
        const { margin } = this.constructor;
        const { left, right } = bubble.getBoundingClientRect();
        const shift = Math.max(margin - left, 0) + Math.min(window.innerWidth - margin - right, 0);
        bubble.style.setProperty("--TutorialPointer__shift", `${shift}px`);
    }

    /**
     * @returns {"out-top"|"out-bottom"|"out-left"|"out-right"|"in"|"unknown"}
     *   where the trigger is now, measured in its scroll parent
     * @private
     */
    _measureTriggerVisibility() {
        if (!this._trigger) {
            return "unknown";
        }
        const rect = this._trigger.getBoundingClientRect();
        const containerRect = (
            closestScrollableY(this._trigger) || document.body
        ).getBoundingClientRect();
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

    /** @private */
    get _trigger() {
        return this.pointerState.trigger;
    }
}
