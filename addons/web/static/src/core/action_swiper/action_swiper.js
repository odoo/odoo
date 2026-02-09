import { useRef } from "@web/owl2/utils";
import { browser } from "@web/core/browser/browser";
import { localization } from "@web/core/l10n/localization";
import { clamp } from "@web/core/utils/numbers";
import { hasTouch } from "@web/core/browser/feature_detection";

import { Component, onMounted, onWillUnmount } from "@odoo/owl";

const isScrollSwipable = (scrollables) => ({
    left: !scrollables.filter((e) => e.scrollLeft !== 0).length,
    right: !scrollables.filter(
        (e) => e.scrollLeft + Math.round(e.getBoundingClientRect().width) !== e.scrollWidth
    ).length,
});

/**
 * Action Swiper
 *
 * This component is intended to perform action once a user has completed a touch swipe.
 * You can choose the direction allowed for such behavior (left, right or both).
 * The action to perform must be passed as a props. It is possible to define a condition
 * to allow the swipe interaction conditionnally.
 * @extends Component
 */
export class ActionSwiper extends Component {
    static template = "web.ActionSwiper";
    static props = {
        onLeftSwipe: {
            type: Object,
            args: {
                action: Function,
                icon: String,
                bgColor: String,
                slot: Object,
            },
            optional: true,
        },
        onRightSwipe: {
            type: Object,
            args: {
                action: Function,
                icon: String,
                bgColor: String,
                slot: Object,
            },
            optional: true,
        },
        enabledDuration: {
            type: Number,
            optional: true
        },
        slots: Object,
        animationType: { type: String, optional: true },
    };
    static defaultProps = {
        onLeftSwipe: undefined,
        onRightSwipe: undefined,
        animationType: "bounce",
    };
    static swipeDistanceRatio = 2;
    static swipeEffectiveThreshold = 20;
    static animationLength = 400;

    setup() {
        this.actionTimeoutId = null;
        this.resetTimeoutId = null;
        this.root = useRef("root");
        this.targetContainer = useRef("targetContainer");
        this.leftPanel = useRef("leftPanel");
        this.rightPanel = useRef("rightPanel");
        this.isSwipeEnabled = false;
        this.scrollables = undefined;
        this.startX = undefined;
        this.swipedDistance = 0;
        this.isSwipeStarted = false;
        const _onTouchMove = (ev) => this._onTouchMoveSwipe(ev);
        const _onTouchEnd = (ev) => this._onTouchEndSwipe(ev);
        onMounted(() => {
            if (this.localizedProps) {
                this.root.el.addEventListener("touchmove", _onTouchMove, { capture: true });
                this.root.el.addEventListener("touchend", _onTouchEnd, { capture: true });
            }
        });
        onWillUnmount(() => {
            browser.clearTimeout(this.actionTimeoutId);
            browser.clearTimeout(this.resetTimeoutId);
            browser.clearTimeout(this.enabledTimeoutId);
        });
    }
    get localizedProps() {
        const onLeftSwipe = localization.direction === "rtl" ? this.props.onRightSwipe : this.props.onLeftSwipe;
        const onRightSwipe = localization.direction === "rtl" ? this.props.onLeftSwipe : this.props.onRightSwipe;
        if (!hasTouch() || (!onRightSwipe && !onLeftSwipe)) {
            return;
        }
        return { onLeftSwipe, onRightSwipe };
    }

    /**
     * @private
     * @param {TouchEvent} ev
     */
    _onTouchEndSwipe(ev) {
        this.isSwipeEnabled = false;
        this.targetContainer.el.classList.add("o_actionswiper_transition_enabled");
        if (this.isSwipeStarted) {
            ev.stopPropagation();
            ev.preventDefault();
            if (this.localizedProps.onRightSwipe && this.swipedDistance > this.containerWidth / this.constructor.swipeDistanceRatio) {
                this.swipedDistance = this.containerWidth;
                this.handleSwipe(this.localizedProps.onRightSwipe.action);
                return;
            } else if (
                this.localizedProps.onLeftSwipe &&
                this.swipedDistance < -this.containerWidth / this.constructor.swipeDistanceRatio
            ) {
                this.swipedDistance = -this.containerWidth;
                this.handleSwipe(this.localizedProps.onLeftSwipe.action);
                return;
            }
        }
        this.targetContainer.el.style.transform = "translateX(0)";
        this.resetTimeoutId = browser.setTimeout(() => this._reset(), this.constructor.animationLength);
    }
    /**
     * @private
     * @param {TouchEvent} ev
     */
    _onTouchMoveSwipe(ev) {
        if (this.isSwipeEnabled) {
            browser.clearTimeout(this.enabledTimeoutId);
            const { onLeftSwipe, onRightSwipe } = this.localizedProps;
            this.swipedDistance = clamp(
                ev.touches[0].clientX - this.startX,
                onLeftSwipe ? -this.containerWidth : 0,
                onRightSwipe ? this.containerWidth : 0
            );
            ev.stopPropagation();
            if (this.isSwipeStarted) {
                // Prevent the browser to navigate back/forward when using swipe
                // gestures while still allowing to scroll vertically.
                ev.preventDefault();
                this.applyStyle(this.swipedDistance);
            } else {
                // If there are scrollable elements under touch pressure,
                // they must be at their limits to allow swiping.
                if (
                    this.scrollables &&
                    !isScrollSwipable(this.scrollables)[this.swipedDistance > 0 ? "left" : "right"]
                ) {
                    return this._reset();
                }
                if (Math.abs(this.swipedDistance) > this.constructor.swipeEffectiveThreshold) {
                    this.isSwipeStarted = true;
                }
            }
        }
    }
    /**
     * @private
     * @param {TouchEvent} ev
     */
    _onTouchStartSwipe(ev) {
        if (this.isSwipeStarted) {
            return;
        }
        this.scrollables = ev
            .composedPath()
            .filter(
                (e) =>
                    e.nodeType === 1 &&
                    this.targetContainer.el.contains(e) &&
                    e.scrollWidth > e.getBoundingClientRect().width &&
                    ["auto", "scroll"].includes(window.getComputedStyle(e)["overflow-x"])
            );
        if (!this.containerWidth) {
            this.containerWidth =
                this.targetContainer && this.targetContainer.el.getBoundingClientRect().width;
        }
        this.isSwipeEnabled = true;
        this.targetContainer.el.classList.remove("o_actionswiper_transition_enabled");
        this.startX = ev.touches[0].clientX;
        if (this.props.enabledDuration) {
            this.enabledTimeoutId = browser.setTimeout(() => this._reset(), this.props.enabledDuration);
        }
    }

    /**
     * @private
     */
    _reset() {
        this.scrollables = undefined;
        this.startX = undefined;
        this.swipedDistance = 0;
        this.isSwipeEnabled = false;
        this.isSwipeStarted = false;
        this.applyStyle(0);
        if (this.targetContainer.el) {
            this.targetContainer.el.classList.add("o_actionswiper_transition_enabled");
        }
    }

    handleSwipe(action) {
        this.applyStyle(this.swipedDistance);
        this.actionTimeoutId = browser.setTimeout(async () => {
            if (this.props.animationType === "bounce") {
                await action();
                this._reset();
            } else if (this.props.animationType === "forwards") {
                await action();
                this.targetContainer.el.classList.remove("o_actionswiper_transition_enabled");
                this.applyStyle(0);
                browser.requestAnimationFrame(() => this._reset());
            }
        }, this.constructor.animationLength);
    }

    applyStyle(distance) {
        if (this.targetContainer.el) {
            this.targetContainer.el.style.transform = distance ? `translateX(${distance}px)` : "";
        }
        if (this.leftPanel.el) { this.leftPanel.el.style.maxWidth = `${distance}px` };
        if (this.rightPanel.el) { this.rightPanel.el.style.maxWidth = `${-distance}px` };
    }
}
