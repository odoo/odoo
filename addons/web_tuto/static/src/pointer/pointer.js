import { Component, onPatched, proxy, signal } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { usePosition } from "@web/core/position/position_hook";
import { closestScrollableY } from "@web/core/utils/scrolling";
import { useDebounced } from "@web/core/utils/timing";
import { pointerState } from "@web_tuto/pointer/pointer_state";

const oppositeSides = {
    left: "right",
    right: "left",
    top: "bottom",
    bottom: "top",
};

const bootstrapSides = {
    left: "start",
    right: "end",
    top: "top",
    bottom: "bottom",
};

/**
 * The pointer of a tutorial: the little ball that follows its trigger, with
 * a bubble next to it explaining what to do, open while the ball or the
 * bubble is hovered (and shortly after, to let the mouse go from one to the
 * other), or always for a hint or when the user always shows the tips. While
 * the trigger is scrolled out of view, the ball waits on the edge of its
 * scroll parent, telling where to scroll.
 */
export class TutorialPointer extends Component {
    static template = "web_tuto.TutorialPointer";
    static margin = 10; // in pixels
    static closeDelay = 300; // in milliseconds

    pointerRef = signal.ref();
    bubbleRef = signal.ref();
    pointerState = pointerState;

    setup() {
        this.state = proxy({
            direction: "bottom",
            triggerPosition: "unknown",
            hoveredTrigger: null,
            hoveredContent: null,
        });
        const pointer = this;
        usePosition(
            this.pointerRef,
            () =>
                this.triggerPosition === "in"
                    ? this._trigger
                    : closestScrollableY(this._trigger) || document.body,
            {
                rememberPosition: false,
                get position() {
                    const triggerPosition = pointer.triggerPosition;
                    const side = triggerPosition.startsWith("out-")
                        ? triggerPosition.slice("out-".length)
                        : pointer.pointerState.position || "bottom";
                    return `${side}-middle`;
                },
                get margin() {
                    const { margin } = pointer.constructor;
                    return pointer.triggerPosition === "in"
                        ? margin
                        : -(pointer.pointerRef().offsetWidth + margin);
                },
                onPositioned: (pointerEl, { direction }) => {
                    const triggerPosition = this.triggerPosition;
                    this.state.triggerPosition = triggerPosition;
                    this.state.direction =
                        triggerPosition === "in" ? direction : oppositeSides[direction];
                    this._keepBubbleInView();
                },
            }
        );
        onPatched(() => this._keepBubbleInView());
        this.closeContent = useDebounced(() => {
            this.state.hoveredTrigger = null;
            this.state.hoveredContent = null;
        }, this.constructor.closeDelay);
    }

    get bubbleSide() {
        return bootstrapSides[this.state.direction];
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
        return this.pointerState.content || "";
    }

    get isVisible() {
        return Boolean(this._trigger?.isConnected);
    }

    get showContent() {
        const { content, hint, tipsShown } = this.pointerState;
        return (
            Boolean(hint || tipsShown) ||
            (this.state.hoveredTrigger === this._trigger && this.state.hoveredContent === content)
        );
    }

    /** @private */
    get _trigger() {
        return this.pointerState.trigger;
    }

    /**
     * Where is the trigger in the scrollParent ?
     * @returns {"out-top"|"out-bottom"|"out-left"|"out-right"|"in"|"unknown"}
     */
    get triggerPosition() {
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

    /**
     * Shifts the bubble centered on the ball so that it doesn't overflow the
     * window, its arrow still pointing at the ball
     * @private
     */
    _keepBubbleInView() {
        const bubble = this.bubbleRef();
        if (!bubble) {
            return;
        }
        bubble.style.removeProperty("--TutorialPointer__shift");
        if (!["top", "bottom"].includes(this.state.direction)) {
            return;
        }
        const { margin } = this.constructor;
        const { left, right } = bubble.getBoundingClientRect();
        const shift = Math.max(margin - left, 0) + Math.min(window.innerWidth - margin - right, 0);
        bubble.style.setProperty("--TutorialPointer__shift", `${shift}px`);
    }

    onContentClick() {
        if (this.triggerPosition !== "in") {
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
}
