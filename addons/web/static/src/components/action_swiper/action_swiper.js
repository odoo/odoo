// @ts-check
/** @odoo-module native */

import { Component, onWillUnmount, status, useRef, useState } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { makeLogger } from "@web/core/debug/debug_logger";
import { reportUncaught } from "@web/core/errors/error_utils";
import { localization } from "@web/core/l10n/localization";
import { Deferred } from "@web/core/utils/concurrency";
import { clamp } from "@web/core/utils/format/numbers";
const log = makeLogger("web.components.action_swiper");

const BOUNCE_ACTION_DELAY = 500;
const FORWARDS_ACTION_DELAY = 100;
const FORWARDS_RESET_DELAY = 100;
const SCROLL_LOCK_THRESHOLD = 40;

/**
 * @param {HTMLElement[]} scrollables
 * @param {"left" | "right"} direction
 * @returns {boolean}
 */
const isScrollSwipable = (scrollables, direction) =>
    scrollables.every((el) => {
        const range = Math.max(0, el.scrollWidth - el.clientWidth);
        const rtl = getComputedStyle(el).direction === "rtl";
        const left = rtl ? -range : 0;
        const right = rtl ? 0 : range;
        // scrollLeft is fractional; clientWidth and scrollWidth are rounded.
        return direction === "left"
            ? el.scrollLeft <= left + 1
            : el.scrollLeft >= right - 1;
    });

export class ActionSwiper extends Component {
    static template = "web.ActionSwiper";
    static props = {
        onLeftSwipe: {
            type: Object,
            shape: {
                action: Function,
                icon: { type: String, optional: true },
                bgColor: { type: String, optional: true },
            },
            optional: true,
        },
        onRightSwipe: {
            type: Object,
            shape: {
                action: Function,
                icon: { type: String, optional: true },
                bgColor: { type: String, optional: true },
            },
            optional: true,
        },
        slots: Object,
        animationOnMove: { type: Boolean, optional: true },
        animationType: { type: String, optional: true },
        swipeDistanceRatio: { type: Number, optional: true },
        swipeInvalid: { type: Function, optional: true },
    };

    static defaultProps = {
        onLeftSwipe: undefined,
        onRightSwipe: undefined,
        animationOnMove: true,
        animationType: "bounce",
        swipeDistanceRatio: 2,
    };

    setup() {
        this.actionTimeoutId = null;
        this.resetTimeoutId = null;
        this.targetContainer = useRef("targetContainer");
        this.rightArea = useRef("rightArea");
        this.leftArea = useRef("leftArea");
        this.state = useState({ isSwiping: false });
        /** @type {number | undefined} */
        this.width = undefined;
        this.scrollables = undefined;
        this.startX = undefined;
        this.swipedDistance = 0;
        this.isScrollValidated = false;
        onWillUnmount(() => {
            browser.clearTimeout(this.actionTimeoutId);
            browser.clearTimeout(this.resetTimeoutId);
        });
    }
    get localizedProps() {
        return {
            onLeftSwipe:
                localization.direction === "rtl"
                    ? this.props.onRightSwipe
                    : this.props.onLeftSwipe,
            onRightSwipe:
                localization.direction === "rtl"
                    ? this.props.onLeftSwipe
                    : this.props.onRightSwipe,
        };
    }

    /** @param {number} distance */
    translate(distance) {
        this.swipedDistance = distance;
        const container = this.targetContainer.el;
        if (!container) {
            return;
        }
        container.style.transform = distance ? `translateX(${distance}px)` : "";
        if (this.rightArea.el) {
            this.rightArea.el.style.maxWidth = `${Math.max(distance, 0)}px`;
        }
        if (this.leftArea.el) {
            this.leftArea.el.style.maxWidth = `${Math.max(-distance, 0)}px`;
        }
    }

    onTouchCancel() {
        if (this.state.isSwiping) {
            this.reset();
        }
    }

    onTouchEnd() {
        if (this.state.isSwiping) {
            this.state.isSwiping = false;
            if (
                this.localizedProps.onRightSwipe &&
                this.swipedDistance > this.width / this.props.swipeDistanceRatio
            ) {
                this.translate(this.width);
                this.handleSwipe(this.localizedProps.onRightSwipe.action);
            } else if (
                this.localizedProps.onLeftSwipe &&
                this.swipedDistance < -this.width / this.props.swipeDistanceRatio
            ) {
                this.translate(-this.width);
                this.handleSwipe(this.localizedProps.onLeftSwipe.action);
            } else {
                this.translate(0);
            }
        }
    }
    /** @param {TouchEvent} ev */
    onTouchMove(ev) {
        if (this.state.isSwiping) {
            if (this.props.swipeInvalid && this.props.swipeInvalid()) {
                this.reset();
                return;
            }
            const { onLeftSwipe, onRightSwipe } = this.localizedProps;
            const distance = clamp(
                ev.touches[0].clientX - this.startX,
                onLeftSwipe ? -this.width : 0,
                onRightSwipe ? this.width : 0,
            );
            if (Math.abs(distance) > SCROLL_LOCK_THRESHOLD) {
                ev.preventDefault();
            }
            if (
                !this.isScrollValidated &&
                this.scrollables &&
                !isScrollSwipable(this.scrollables, distance > 0 ? "left" : "right")
            ) {
                this.reset();
                return;
            }
            this.isScrollValidated = true;

            if (this.props.animationOnMove) {
                this.translate(distance);
            } else {
                this.swipedDistance = distance;
            }
        }
    }
    /** @param {TouchEvent} ev */
    onTouchStart(ev) {
        this.scrollables = /** @type {HTMLElement[]} */ (
            ev.composedPath().filter((e) => {
                const el = /** @type {HTMLElement} */ (e);
                return (
                    el.nodeType === 1 &&
                    this.targetContainer.el.contains(el) &&
                    el.scrollWidth > el.clientWidth &&
                    ["auto", "scroll"].includes(
                        window.getComputedStyle(el)["overflow-x"],
                    )
                );
            })
        );
        this.width = this.targetContainer.el?.getBoundingClientRect().width;
        this.state.isSwiping = true;
        this.isScrollValidated = false;
        this.startX = ev.touches[0].clientX;
    }

    reset() {
        this.state.isSwiping = false;
        this.translate(0);
        this.width = undefined;
        this.scrollables = undefined;
        this.startX = undefined;
        this.isScrollValidated = false;
    }

    /** @param {any} error */
    reportActionError(error) {
        reportUncaught(error);
    }

    handleSwipe(action) {
        log.logic("handleSwipe", () => ({
            animationType: this.props.animationType,
            swipedDistance: this.swipedDistance,
        }));
        browser.clearTimeout(this.actionTimeoutId);
        browser.clearTimeout(this.resetTimeoutId);
        if (this.props.animationType === "bounce") {
            this.translate(this.swipedDistance);
            this.actionTimeoutId = browser.setTimeout(async () => {
                try {
                    await action(Promise.resolve());
                } catch (error) {
                    this.reportActionError(error);
                }
                if (status(this) === "destroyed") {
                    return;
                }
                this.reset();
            }, BOUNCE_ACTION_DELAY);
        } else if (this.props.animationType === "forwards") {
            this.translate(this.swipedDistance);
            this.actionTimeoutId = browser.setTimeout(async () => {
                const prom = new Deferred();
                try {
                    await action(prom);
                } catch (error) {
                    this.reportActionError(error);
                }
                if (status(this) === "destroyed") {
                    prom.resolve();
                    return;
                }
                this.state.isSwiping = true;
                this.translate(-this.swipedDistance);
                this.resetTimeoutId = browser.setTimeout(() => {
                    prom.resolve();
                    this.reset();
                }, FORWARDS_RESET_DELAY);
            }, FORWARDS_ACTION_DELAY);
        } else {
            return action(Promise.resolve());
        }
    }
}
