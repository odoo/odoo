import { Component, computed, onPatched, signal, useOnChange } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { usePosition } from "@web/core/position/position_hook";
import { closestScrollableY, getPositionInContainer } from "@web/core/utils/scrolling";
import { useDebounced } from "@web/core/utils/timing";
import { pointerState } from "@web_tutorial/pointer/pointer_state";

/**
 * For each side of a trigger: the side of a Bootstrap popover there, the
 * opposite side, and the hint to scroll to a trigger out of view on that side
 */
const SIDES = {
    bottom: {
        bootstrap: "bottom",
        opposite: "top",
        scrollHint: _t("Scroll down to reach the next step."),
    },
    left: {
        bootstrap: "start",
        opposite: "right",
        scrollHint: _t("Scroll left to reach the next step."),
    },
    right: {
        bootstrap: "end",
        opposite: "left",
        scrollHint: _t("Scroll right to reach the next step."),
    },
    top: {
        bootstrap: "top",
        opposite: "bottom",
        scrollHint: _t("Scroll up to reach the next step."),
    },
};

/**
 * A ball following its trigger, with a bubble explaining what to do, open
 * while hovered or always (e.g. a skippable step); a tutorial expanding its
 * messages shows the bubble alone. While the trigger is out of view, the ball
 * waits on the edge of its scroll parent.
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
    /**
     * Where the trigger was when the ball was last placed: in view, or the
     * side it was out of view on
     */
    triggerVisibility = signal("unknown");

    bubbleSide = computed(() => SIDES[this.side()]?.bootstrap);
    /**
     * Where to scroll while the trigger is out of view (but for a centered
     * bubble), the help otherwise
     */
    content = computed(
        () =>
            (!this.pointerState.centered && SIDES[this.triggerVisibility()]?.scrollHint) ||
            this.pointerState.content ||
            ""
    );
    /** Whether Next is shown: in a centered bubble, or with its trigger in view */
    isNextShown = computed(
        () =>
            Boolean(this.pointerState.onNext) &&
            (this.pointerState.centered || this.triggerVisibility() === "in")
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
                        triggerVisibility === "in" ? direction : SIDES[direction]?.opposite
                    );
                    this.#keepBubbleInView();
                },
                get position() {
                    const triggerVisibility = pointer.#measureTriggerVisibility();
                    return `${triggerVisibility in SIDES ? triggerVisibility : "bottom"}-middle`;
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
     * @returns {"in"|"unknown"|keyof SIDES} where the trigger is now, in view
     *   or the side of its scroll parent it's out of view on
     */
    #measureTriggerVisibility() {
        const { trigger } = this.pointerState;
        if (!trigger) {
            return "unknown";
        }
        const position = getPositionInContainer(
            trigger,
            closestScrollableY(trigger) || document.body
        );
        return position.replace("out-", "");
    }
}
