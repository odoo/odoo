import {
    Component,
    onMounted,
    onPatched,
    onWillUnmount,
    proxy,
    signal,
    t,
    useProps,
} from "@odoo/owl";
import { useBus, useService } from "@web/core/utils/hooks";
import { usePosition } from "@web/core/position/position_hook";
import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";

const oppositeSides = {
    left: "right",
    right: "left",
    top: "bottom",
    bottom: "top",
};

/**
 * @param {HTMLElement} element
 * @returns {HTMLElement | null}
 */
function getScrollParent(element) {
    if (!element) {
        return null;
    }
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

/**
 * @typedef TutorialPointerState
 * @property {HTMLElement} [trigger]
 * @property {string} [content]
 * @property {Direction} [position]
 * @property {() => void} [onNext]
 * @property {() => void} [onSkip]
 */
export const pointerState = proxy({
    trigger: undefined,
    content: "",
    position: "bottom",
    onNext: undefined,
    onSkip: undefined,
});

class TutorialPointerPopover extends Component {
    static template = "web_tuto.TutorialPointer.Content";

    props = useProps({
        content: t.string(),
        close: t.function(),
        onClick: t.function(),
        onNext: t.function().optional(),
        onSkip: t.function().optional(),
    });
}

/**
 * The pointer of a tutorial: the little ball that follows its trigger, with
 * a bubble always open next to it, explaining what to do.
 */
export class TutorialPointer extends Component {
    props = useProps({
        pointerState: t.object({
            trigger: t.instanceOf(HTMLElement).optional(),
            content: t.string().optional(),
            position: t.selection(["left", "right", "top", "bottom"]).optional(),
            onNext: t.function().optional(),
            onSkip: t.function().optional(),
        }),
    });

    static template = "web_tuto.TutorialPointer";
    static width = 28; // in pixels
    static height = 28; // in pixels

    anchorRef = signal.ref();
    pointerRef = signal.ref();

    setup() {
        this.state = proxy({
            direction: "bottom", //The side towards which the ball hangs
            triggerPosition: "unknown",
            scrollParent: undefined,
            triggerBelow: false,
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
            this.anchorRef,
            () => this.scrollParent,
            anchorPositionOptions
        );

        const pointerPositionOptions = {
            margin: 10,
            onPositioned: (pointer, position) => {
                // When trigger position changes (in <=> out)
                const triggerPosition = this.triggerPosition;
                if (triggerPosition !== this.state.triggerPosition) {
                    this.state.triggerPosition = triggerPosition;
                    this.openContent();
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
            get: () => `${this.pointerPosition}-middle`,
            set: () => {},
            enumerable: true,
        });

        this.pointerUsePosition = usePosition(
            this.pointerRef,
            () => (this.triggerPosition === "in" ? this.trigger : this.anchorRef()),
            pointerPositionOptions
        );

        const uiService = useService("ui");
        const onActiveElementChanged = () => {
            const activeEl = uiService.activeElement;
            const trigger = this.trigger;
            if (trigger) {
                const frameEl =
                    trigger.ownerDocument !== document
                        ? trigger.ownerDocument.defaultView?.frameElement
                        : trigger;
                this.state.triggerBelow = frameEl ? !activeEl.contains(frameEl) : true;
            }
        };
        useBus(uiService.bus, "active-element-changed", onActiveElementChanged);

        let lastTrigger;
        let lastContent;
        const applyTriggerEffect = () => {
            const trigger = this.trigger;
            if (!trigger) {
                this.popover.close();
                return;
            }
            onActiveElementChanged();
            this.state.scrollParent = getScrollParent(trigger);
            this.anchorUsePosition.unlock();
            this.pointerUsePosition.unlock();
            this.openContent();
        };
        onMounted(() => {
            lastTrigger = this.trigger;
            lastContent = this.props.pointerState.content;
            applyTriggerEffect();
        });
        // Not useOnChange: its microtask would unlock usePosition before the patch settles
        onPatched(() => {
            const trigger = this.trigger;
            const content = this.props.pointerState.content;
            if (trigger !== lastTrigger || content !== lastContent) {
                lastTrigger = trigger;
                lastContent = content;
                applyTriggerEffect();
            } else if (!this.isVisible) {
                this.popover.close();
            } else if (!this.popover.isOpen) {
                this.openContent();
            }
        });
        onWillUnmount(() => this.popover.close());

        const popoverOptions = {
            setActiveElement: false,
            closeOnClickAway: false,
            closeOnEscape: false,
        };

        Object.defineProperty(popoverOptions, "position", {
            get: () => `${this.pointerPosition}-middle`,
            set: () => {},
            enumerable: true,
        });

        this.popover = usePopover(TutorialPointerPopover, popoverOptions);
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
        return (
            this.trigger?.isConnected &&
            this.triggerPosition !== "unknown" &&
            !this.state.triggerBelow
        );
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
     * @returns {"out-top"|"out-bottom"|"out-left"|"out-right"|"in"|"unknown"}
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

    /**
     * (Re)opens the bubble, which stays open as long as the trigger is shown
     */
    openContent() {
        this.popover.close();
        if (!this.isVisible || !this.content) {
            return;
        }
        const inView = this.triggerPosition === "in";
        this.popover.open(inView ? this.pointerRef() || this.trigger : this.anchorRef(), {
            content: this.content,
            onNext: inView ? this.props.pointerState.onNext : undefined,
            onSkip: this.props.pointerState.onSkip,
            onClick: () => {
                if (this.triggerPosition !== "in") {
                    this.trigger.scrollIntoView({ behavior: "smooth", block: "nearest" });
                }
            },
        });
    }
}
