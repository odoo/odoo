import { browser } from "@web/core/browser/browser";
import { localization } from "@web/core/l10n/localization";
import { clamp } from "@web/core/utils/numbers";
import { hasTouch } from "@web/core/browser/feature_detection";

import { Component, onMounted, onWillUnmount, props, signal, t } from "@odoo/owl";

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
    props = props({
        onLeftSwipe: onSwipeType.optional(),
        onRightSwipe: onSwipeType.optional(),
        enabledDuration: t.number().optional(),
        slots: t.object(),
        animationType: t.string().optional("bounce"),
    });
    static swipeDistanceRatio = 3;
    static swipeEffectiveThreshold = 20;
    // A quick flick commits the swipe regardless of distance (px/ms).
    static swipeVelocityThreshold = 0.2;
    static swipeStartMaxDelay = 300;
    static animationLength = 400;

    root = signal(null);
    targetContainer = signal(null);
    leftPanel = signal(null);
    rightPanel = signal(null);

    setup() {
        super.setup();
        this.actionTimeoutId = null;
        this.resetTimeoutId = null;
        this.isSwipeEnabled = false;
        this.scrollables = undefined;
        this.startX = undefined;
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
        this.isSwipeEnabled = false;
        this.targetContainer().classList.add("o_actionswiper_transition_enabled");
        // A quick flick counts as a swipe even when the drag never passed the
        // "started" distance threshold; otherwise a short fast swipe slips
        // through as a click on the underlying content. A tap is excluded by
        // requiring both a real velocity and some minimal movement.
        const elapsed = Date.now() - this.startClock;
        const velocity = elapsed > 0 ? this.swipedDistance / elapsed : 0;
        const isFlick =
            Math.abs(velocity) > this.constructor.swipeVelocityThreshold &&
            Math.abs(this.swipedDistance) > this.constructor.swipeEffectiveThreshold / 2;
        if (this.isSwipeStarted || isFlick) {
            ev.stopPropagation();
            ev.preventDefault();
            const threshold = this.containerWidth / this.constructor.swipeDistanceRatio;
            if (
                this.localizedProps.onRightSwipe &&
                this.swipedDistance > 0 &&
                (this.swipedDistance > threshold || isFlick)
            ) {
                this.swipedDistance = this.containerWidth;
                this.handleSwipe(this.localizedProps.onRightSwipe.action);
                return;
            } else if (
                this.localizedProps.onLeftSwipe &&
                this.swipedDistance < 0 &&
                (-this.swipedDistance > threshold || isFlick)
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
                    if (
                        ev.timeStamp - this.startTime > this.constructor.swipeStartMaxDelay ||
                        !ev.cancelable
                    ) {
                        return this._reset();
                    }
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
                    this.targetContainer().contains(e) &&
                    e.scrollWidth > e.getBoundingClientRect().width &&
                    ["auto", "scroll"].includes(window.getComputedStyle(e)["overflow-x"])
            );
        if (!this.containerWidth) {
            this.containerWidth =
                this.targetContainer() && this.targetContainer().getBoundingClientRect().width;
        }
        this.isSwipeEnabled = true;
        this.targetContainer().classList.remove("o_actionswiper_transition_enabled");
        this.startX = ev.touches[0].clientX;
        this.startTime = ev.timeStamp;
        // Wall-clock start for the flick velocity: unlike the event's real
        // timeStamp (used by swipeStartMaxDelay), Date.now() is mockable in
        // tests (driven by advanceTime), so a synthetic drag isn't a "flick".
        this.startClock = Date.now();
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
