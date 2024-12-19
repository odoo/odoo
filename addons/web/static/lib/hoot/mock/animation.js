/** @odoo-module */

import { on } from "@odoo/hoot-dom";
import { MockEventTarget } from "../hoot_utils";

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const {
    Array: { isArray: $isArray },
    Element,
    Object: { entries: $entries },
    scroll: windowScroll,
    scrollBy: windowScrollBy,
    scrollTo: windowScrollTo,
} = globalThis;

const { animate, scroll, scrollBy, scrollIntoView, scrollTo } = Element.prototype;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

const forceInstantScroll = (args) =>
    !allowAnimations && args[0] && typeof args[0] === "object"
        ? [{ ...args[0], behavior: "instant" }, ...args.slice(1)]
        : args;

const animationChangeBus = new MockEventTarget();
const animationChangeCleanups = [];

let allowAnimations = false;

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

export class MockAnimation extends MockEventTarget {
    static publicListeners = ["cancel", "finish", "remove"];

    currentTime = null;
    effect = null;
    finished = Promise.resolve(this);
    id = "";
    pending = false;
    playState = "idle";
    playbackRate = 1;
    ready = Promise.resolve(this);
    replaceState = "active";
    startTime = null;
    timeline = {
        currentTime: this.currentTime,
        duration: null,
    };

    cancel() {
        this.dispatchEvent(new AnimationPlaybackEvent("cancel"));
    }

    commitStyles() {}

    finish() {
        this.dispatchEvent(new AnimationPlaybackEvent("finish"));
    }

    pause() {}

    persist() {}

    play() {
        this.dispatchEvent(new AnimationPlaybackEvent("finish"));
    }

    reverse() {}

    updatePlaybackRate() {}
}

export function cleanupAnimations() {
    allowAnimations = false;

    while (animationChangeCleanups.length) {
        animationChangeCleanups.pop()();
    }
}

/**
 * @param {boolean} [enable]
 */
export function enableAnimations(enable = true) {
    allowAnimations = enable;

    animationChangeBus.dispatchEvent(new CustomEvent("toggle-animations"));
}

/** @type {typeof Element["prototype"]["animate"]} */
export function mockedAnimate(...args) {
    if (allowAnimations) {
        return animate.call(this, ...args);
    }

    // Apply style properties immediatly
    const keyframesList = $isArray(args[0]) ? args[0] : [args[0]];
    const style = {};
    for (const kf of keyframesList) {
        for (const [key, value] of $entries(kf)) {
            style[key] = $isArray(value) ? value.at(-1) : value;
        }
    }
    Object.assign(this.style, style);

    // Return mock animation
    return new MockAnimation();
}

/** @type {typeof Element["prototype"]["scroll"]} */
export function mockedScroll(...args) {
    return scroll.call(this, ...forceInstantScroll(args));
}

/** @type {typeof Element["prototype"]["scrollBy"]} */
export function mockedScrollBy(...args) {
    return scrollBy.call(this, ...forceInstantScroll(args));
}

/** @type {typeof Element["prototype"]["scrollIntoView"]} */
export function mockedScrollIntoView(...args) {
    return scrollIntoView.call(this, ...forceInstantScroll(args));
}

/** @type {typeof Element["prototype"]["scrollTo"]} */
export function mockedScrollTo(...args) {
    return scrollTo.call(this, ...forceInstantScroll(args));
}

/** @type {typeof window["scroll"]} */
export function mockedWindowScroll(...args) {
    return windowScroll.call(this, ...forceInstantScroll(args));
}

/** @type {typeof window["scrollBy"]} */
export function mockedWindowScrollBy(...args) {
    return windowScrollBy.call(this, ...forceInstantScroll(args));
}

/** @type {typeof window["scrollTo"]} */
export function mockedWindowScrollTo(...args) {
    return windowScrollTo.call(this, ...forceInstantScroll(args));
}

/**
 * @param {(allowAnimations: boolean) => any} onChange
 */
export function subscribeToAnimationChange(onChange) {
    onChange(allowAnimations);
    animationChangeCleanups.push(
        on(animationChangeBus, "toggle-animations", () => onChange(allowAnimations))
    );
}
