import { Component, computed, onPatched, signal, useOnChange } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { usePosition } from "@web/core/position/position_hook";
import { closestScrollableY, getPositionInContainer } from "@web/core/utils/scrolling";
import { useDebounced } from "@web/core/utils/timing";
import { pointerState } from "@web_tutorial/pointer/pointer_state";

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

const scrollHints = {
    "out-bottom": _t("Scroll down to reach the next step."),
    "out-left": _t("Scroll left to reach the next step."),
    "out-right": _t("Scroll right to reach the next step."),
    "out-top": _t("Scroll up to reach the next step."),
};

const outOfViewSides = {
    "out-bottom": "bottom",
    "out-left": "left",
    "out-right": "right",
    "out-top": "top",
};

/**
 * A ball following its trigger, with a bubble explaining what to do, open
 * while hovered or always (e.g. a hint); a tutorial always showing it shows
 * the bubble alone. While the trigger is out of view, the ball waits on the
 * edge of its scroll parent.
 */
export class TutorialPointer extends Component {
    /** How long the bubble stays open after the mouse left, in milliseconds */
    static closeDelay = 300;
    /** The space between the ball and its trigger, in pixels */
    static margin = 10;
    static template = "web_tutorial.TutorialPointer";

    bubbleRef = signal.ref();
    /** What was hovered, the bubble staying open while still pointed */
    hoveredContent = signal(null);
    hoveredTrigger = signal(null);
    pointerRef = signal.ref();
    pointerState = pointerState;
    /** The side of its trigger (or of the edge) the ball is on */
    side = signal("bottom");
    /** Whether the trigger was in view when the ball was last placed */
    triggerVisibility = signal("unknown");

    bubbleSide = computed(() => bootstrapSides[this.side()]);
    /** Where to scroll while the trigger is out of view, the help otherwise */
    content = computed(
        () => scrollHints[this.triggerVisibility()] || this.pointerState.content || ""
    );
    /**
     * The steps of each chapter of the tutorial, for its progress bar:
     * "done" before the pointed one, then "current" and "todo"
     */
    progressBar = computed(() => {
        const { chapterSizes, stepIndex } = this.pointerState;
        let index = 0;
        return chapterSizes.split(",").map((size) =>
            Array.from({ length: Number(size) }, () => {
                const state = index < stepIndex ? "done" : index === stepIndex ? "current" : "todo";
                index++;
                return state;
            })
        );
    });
    showContent = computed(() => {
        const { alwaysOpen, content, trigger } = this.pointerState;
        return (
            Boolean(alwaysOpen) ||
            (this.hoveredTrigger() === trigger && this.hoveredContent() === content)
        );
    });

    /**
     * Places the ball next to its trigger, or inside the edge of its scroll
     * parent (a negative margin) while the trigger is out of view
     */
    setup() {
        const pointer = this;
        const position = usePosition(
            this.pointerRef,
            () =>
                this.#measureTriggerVisibility() === "in"
                    ? this.pointerState.trigger
                    : closestScrollableY(this.pointerState.trigger) || document.body,
            {
                get margin() {
                    const { margin } = pointer.constructor;
                    return pointer.#measureTriggerVisibility() === "in"
                        ? margin
                        : -(pointer.pointerRef().offsetWidth + margin);
                },
                onPositioned: (pointerEl, { direction }) => {
                    const triggerVisibility = this.#measureTriggerVisibility();
                    this.triggerVisibility.set(triggerVisibility);
                    this.side.set(
                        triggerVisibility === "in" ? direction : oppositeSides[direction]
                    );
                    this.#keepBubbleInView();
                },
                get position() {
                    const triggerVisibility = pointer.#measureTriggerVisibility();
                    return `${outOfViewSides[triggerVisibility] || "bottom"}-middle`;
                },
                rememberPosition: false,
            }
        );
        useOnChange(
            () => [this.pointerState.triggerRect],
            () => position.unlock(),
            { initialRun: false }
        );
        onPatched(() => this.#keepBubbleInView());
        this.closeContent = useDebounced(() => {
            this.hoveredTrigger.set(null);
            this.hoveredContent.set(null);
        }, this.constructor.closeDelay);
    }

    get isVisible() {
        return Boolean(this.pointerState.trigger?.isConnected);
    }

    onContentClick() {
        if (this.triggerVisibility() !== "in") {
            this.pointerState.trigger.scrollIntoView({ behavior: "smooth", block: "nearest" });
        }
    }

    onMouseEnter() {
        this.closeContent.cancel();
        this.hoveredTrigger.set(this.pointerState.trigger);
        this.hoveredContent.set(this.pointerState.content);
    }

    onMouseLeave() {
        this.closeContent();
    }

    /**
     * Shifts the bubble so that it doesn't overflow the window
     */
    #keepBubbleInView() {
        const bubble = this.bubbleRef();
        if (!bubble) {
            return;
        }
        bubble.style.removeProperty("--TutorialPointer__shift");
        if (!["top", "bottom"].includes(this.side())) {
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
     */
    #measureTriggerVisibility() {
        const { trigger } = this.pointerState;
        if (!trigger) {
            return "unknown";
        }
        return getPositionInContainer(trigger, closestScrollableY(trigger) || document.body);
    }
}
