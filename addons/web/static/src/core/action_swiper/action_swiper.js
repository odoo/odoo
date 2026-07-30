import { browser } from "@web/core/browser/browser";
import { localization } from "@web/core/l10n/localization";
import { clamp } from "@web/core/utils/numbers";
import { hasTouch } from "@web/core/browser/feature_detection";

import { Component, onMounted, onWillUnmount, signal, t, useProps } from "@odoo/owl";

const isScrollSwipable = (scrollables) => ({
    left: !scrollables.filter((e) => e.scrollLeft !== 0).length,
    right: !scrollables.filter(
        (e) => e.scrollLeft + Math.round(e.getBoundingClientRect().width) !== e.scrollWidth
    ).length,
});

export const onSwipeType = t.object({
    action: t.function().optional(),
    bgColor: t.string().optional(),
    icon: t.string().optional(),
    slot: t.object().optional(),
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
    props = useProps({
        onLeftSwipe: onSwipeType.optional(),
        onRightSwipe: onSwipeType.optional(),
        enabledDuration: t.number().optional(),
        slots: t.object(),
        animationType: t.string().optional("bounce"),
    });
    static swipeDistanceRatio = 3;
    static swipeEffectiveThreshold = 10;
    static animationLength = 400;

    root = signal.ref();
    targetContainer = signal.ref();
    leftPanel = signal.ref();
    rightPanel = signal.ref();

    setup() {
        super.setup();
        this.actionTimeoutId = null;
        this.resetTimeoutId = null;
        this.isSwipeEnabled = false;
        this.scrollables = undefined;
        this.startX = undefined;
        this.startY = undefined;
        this.swipeAxis = null;
        this.isVerticalScroll = false;
        this.swipedDistance = 0;
        this.isSwipeStarted = false;
        const _onTouchMove = (ev) => this._onTouchMoveSwipe(ev);
        const _onTouchEnd = (ev) => this._onTouchEndSwipe(ev);
        onMounted(() => {
            if (this.localizedProps) {
                this.root().addEventListener("touchmove", _onTouchMove, { capture: true });
                this.root().addEventListener("touchend", _onTouchEnd, { capture: true });
            }
        });
        onWillUnmount(() => {
            browser.clearTimeout(this.actionTimeoutId);
            browser.clearTimeout(this.resetTimeoutId);
            browser.clearTimeout(this.enabledTimeoutId);
        });
    }
    get localizedProps() {
        const onLeftSwipe =
            localization.direction === "rtl" ? this.props.onRightSwipe : this.props.onLeftSwipe;
        const onRightSwipe =
            localization.direction === "rtl" ? this.props.onLeftSwipe : this.props.onRightSwipe;
        if (!hasTouch() || (!onRightSwipe && !onLeftSwipe)) {
            return null;
        }
        return { onLeftSwipe, onRightSwipe };
    }

    /**
     * @private
     * @param {TouchEvent} ev
     */
    _onTouchEndSwipe(ev) {
        if (this.isVerticalScroll) {
            ev.stopPropagation();
            this.isVerticalScroll = false;
            return;
        }
        this.isSwipeEnabled = false;
        this.targetContainer().classList.add("o_actionswiper_transition_enabled");
        if (this.isSwipeStarted) {
            ev.stopPropagation();
            ev.preventDefault();
            if (
                this.localizedProps.onRightSwipe &&
                this.swipedDistance > this.containerWidth / this.constructor.swipeDistanceRatio
            ) {
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
        this.targetContainer().style.transform = "translateX(0)";
        this.resetTimeoutId = browser.setTimeout(
            () => this._reset(),
            this.constructor.animationLength
        );
    }
    /**
     * @private
     * @param {TouchEvent} ev
     */
    _onTouchMoveSwipe(ev) {
        if (this.isVerticalScroll) {
            ev.stopPropagation();
            return;
        }
        if (this.isSwipeEnabled) {
            browser.clearTimeout(this.enabledTimeoutId);
            const { onLeftSwipe, onRightSwipe } = this.localizedProps;

            // Determine the dominant axis of swiping to prevent scrolling on the vertical axis
            // and swiping on the horizontal axis at the same time.
            if (!this.swipeAxis) {
                const deltaX = ev.touches[0].clientX - this.startX;
                const deltaY = ev.touches[0].clientY - this.startY;
                if (
                    Math.abs(deltaX) < this.constructor.swipeEffectiveThreshold &&
                    Math.abs(deltaY) < this.constructor.swipeEffectiveThreshold
                ) {
                    ev.stopPropagation();
                    return; // not enough movement yet to decide, don't touch native scroll
                }
                this.swipeAxis = Math.abs(deltaX) >= Math.abs(deltaY) ? "x" : "y";
                if (this.swipeAxis === "y") {
                    this.isVerticalScroll = true;
                    ev.stopPropagation();
                    this._reset();
                    return;
                }
            }

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
                    this.applyStyle(this.swipedDistance);
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
                    this.targetContainer().contains(e) &&
                    e.scrollWidth > e.getBoundingClientRect().width &&
                    ["auto", "scroll"].includes(window.getComputedStyle(e)["overflow-x"])
            );
        if (!this.containerWidth) {
            this.containerWidth =
                this.targetContainer() && this.targetContainer().getBoundingClientRect().width;
        }
        this.isSwipeEnabled = true;
        this.isVerticalScroll = false;
        this.targetContainer().classList.remove("o_actionswiper_transition_enabled");
        this.startX = ev.touches[0].clientX;
        this.startY = ev.touches[0].clientY;
        this.swipeAxis = null;
        if (this.props.enabledDuration) {
            this.enabledTimeoutId = browser.setTimeout(
                () => this._reset(),
                this.props.enabledDuration
            );
        }
    }

    /**
     * @private
     */
    _reset() {
        this.scrollables = undefined;
        this.startX = undefined;
        this.startY = undefined;
        this.swipeAxis = null;
        this.swipedDistance = 0;
        this.isSwipeEnabled = false;
        this.isSwipeStarted = false;
        this.applyStyle(0);
        if (this.targetContainer()) {
            this.targetContainer().classList.add("o_actionswiper_transition_enabled");
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
                this.targetContainer().classList.remove("o_actionswiper_transition_enabled");
                this.applyStyle(0);
                browser.requestAnimationFrame(() => this._reset());
            }
        }, this.constructor.animationLength);
    }

    applyStyle(distance) {
        if (this.targetContainer()) {
            this.targetContainer().style.transform = distance ? `translateX(${distance}px)` : "";
        }
        if (this.leftPanel()) {
            this.leftPanel().style.maxWidth = `${distance}px`;
        }
        if (this.rightPanel()) {
            this.rightPanel().style.maxWidth = `${-distance}px`;
        }
    }
}
