/** @odoo-module **/
import { browser } from "@web/core/browser/browser";
import { localization } from "@web/core/l10n/localization";
import { clamp } from "@web/core/utils/numbers";

import { Component, onMounted, onWillUnmount, useRef, useState } from "@odoo/owl";

const isScrollSwipable = (scrollables) => {
    return {
        left: !scrollables.filter((e) => e.scrollLeft !== 0).length,
        right: !scrollables.filter(
            (e) => e.scrollLeft + Math.round(e.getBoundingClientRect().width) !== e.scrollWidth
        ).length,
    };
};

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
    setup() {
        this.actionTimeoutId = null;
        this.resetTimeoutId = null;
        this.defaultState = {
            containerStyle: "",
            isSwiping: false,
            width: undefined,
        };
        this.root = useRef("root");
        this.targetContainer = useRef("targetContainer");
        this.state = useState({ ...this.defaultState });
        this.scrollables = undefined;
        this.startX = undefined;
        this.swipedDistance = 0;
        this.isScrollValidated = false;
        onMounted(() => {
            if (this.targetContainer.el) {
                this.state.width = this.targetContainer.el.getBoundingClientRect().width;
            }
            // Forward classes set on component to slot, as we only want to wrap an
            // existing component without altering the DOM structure any more than
            // strictly necessary
            if (this.props.onLeftSwipe || this.props.onRightSwipe) {
                const classes = new Set(this.root.el.classList);
                classes.delete("o_actionswiper");
                for (const className of classes) {
                    this.targetContainer.el.firstChild.classList.add(className);
                    this.root.el.classList.remove(className);
                }
            }
        });
        onWillUnmount(() => {
            browser.clearTimeout(this.actionTimeoutId);
            browser.clearTimeout(this.resetTimeoutId);
        });
    }
    get localizedProps() {
        return {
            onLeftSwipe:
                localization.direction === "rtl" ? this.props.onRightSwipe : this.props.onLeftSwipe,
            onRightSwipe:
                localization.direction === "rtl" ? this.props.onLeftSwipe : this.props.onRightSwipe,
        };
    }

    /**
     * @private
     * @param {TouchEvent} ev
     */
    _onTouchEndSwipe() {
        if (this.state.isSwiping) {
            this.state.isSwiping = false;
            if (
                this.localizedProps.onRightSwipe &&
                this.swipedDistance > this.state.width / this.props.swipeDistanceRatio
            ) {
                this.swipedDistance = this.state.width;
                this.handleSwipe(this.localizedProps.onRightSwipe.action);
            } else if (
                this.localizedProps.onLeftSwipe &&
                this.swipedDistance < -this.state.width / this.props.swipeDistanceRatio
            ) {
                this.swipedDistance = -this.state.width;
                this.handleSwipe(this.localizedProps.onLeftSwipe.action);
            } else {
                this.state.containerStyle = "";
            }
        }
    }
    /**
     * @private
     * @param {TouchEvent} ev
     */
    _onTouchMoveSwipe(ev) {
        if (this.state.isSwiping) {
            if (this.props.swipeInvalid && this.props.swipeInvalid()) {
                this.state.isSwiping = false;
                return;
            }
            const { onLeftSwipe, onRightSwipe } = this.localizedProps;
            this.swipedDistance = clamp(
                ev.touches[0].clientX - this.startX,
                onLeftSwipe ? -this.state.width : 0,
                onRightSwipe ? this.state.width : 0
            );
            // Prevent the browser to navigate back/forward when using swipe
            // gestures while still allowing to scroll vertically.
            if (Math.abs(this.swipedDistance) > 40) {
                ev.preventDefault();
            }
            // If there are scrollable elements under touch pressure,
            // they must be at their limits to allow swiping.
            if (
                !this.isScrollValidated &&
                this.scrollables &&
                !isScrollSwipable(this.scrollables)[this.swipedDistance > 0 ? "left" : "right"]
            ) {
                return this._reset();
            }
            this.isScrollValidated = true;

            if (this.props.animationOnMove) {
                this.state.containerStyle = `transform: translateX(${this.swipedDistance}px)`;
            }
        }
    }
    /**
     * @private
     * @param {TouchEvent} ev
     */
    _onTouchStartSwipe(ev) {
        this.scrollables = ev
            .composedPath()
            .filter(
                (e) =>
                    e.nodeType === 1 &&
                    this.targetContainer.el.contains(e) &&
                    e.scrollWidth > e.getBoundingClientRect().width &&
                    ["auto", "scroll"].includes(window.getComputedStyle(e)["overflow-x"])
            );
        if (!this.state.width) {
            this.state.width =
                this.targetContainer && this.targetContainer.el.getBoundingClientRect().width;
        }
        this.state.isSwiping = true;
        this.isScrollValidated = false;
        this.startX = ev.touches[0].clientX;
    }

    /**
     * @private
     */
    _reset() {
        Object.assign(this.state, { ...this.defaultState });
        this.scrollables = undefined;
        this.startX = undefined;
        this.swipedDistance = 0;
        this.isScrollValidated = false;
    }

    handleSwipe(action) {
        if (this.props.animationType === "bounce") {
            this.state.containerStyle = `transform: translateX(${this.swipedDistance}px)`;
            this.actionTimeoutId = browser.setTimeout(async () => {
                await action();
                this._reset();
            }, 500);
        } else if (this.props.animationType === "forwards") {
            this.state.containerStyle = `transform: translateX(${this.swipedDistance}px)`;
            this.actionTimeoutId = browser.setTimeout(async () => {
                await action();
                this.state.isSwiping = true;
                this.state.containerStyle = `transform: translateX(${-this.swipedDistance}px)`;
                this.resetTimeoutId = browser.setTimeout(() => {
                    this._reset();
                }, 100);
            }, 100);
        } else {
            return action();
        }
    }
}

ActionSwiper.props = {
    onLeftSwipe: {
        type: Object,
        args: {
            action: Function,
            icon: String,
            bgColor: String,
        },
        optional: true,
    },
    onRightSwipe: {
        type: Object,
        args: {
            action: Function,
            icon: String,
            bgColor: String,
        },
        optional: true,
    },
    slots: Object,
    animationOnMove: { type: Boolean, optional: true },
    animationType: { type: String, optional: true },
    swipeDistanceRatio: { type: Number, optional: true },
    swipeInvalid: { type: Function, optional: true },
};

ActionSwiper.defaultProps = {
    onLeftSwipe: undefined,
    onRightSwipe: undefined,
    animationOnMove: true,
    animationType: "bounce",
    swipeDistanceRatio: 2,
};

ActionSwiper.template = "web.ActionSwiper";
