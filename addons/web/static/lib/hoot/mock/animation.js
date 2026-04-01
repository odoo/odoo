/** @odoo-module */

import { on } from "@odoo/hoot-dom";
import { MockEventTarget } from "../hoot_utils";
import { ensureTest } from "../main_runner";

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const {
    Array: { isArray: $isArray },
    Element,
    Object: { assign: $assign, entries: $entries },
    scroll: windowScroll,
    scrollBy: windowScrollBy,
    scrollTo: windowScrollTo,
} = globalThis;

const { animate, scroll, scrollBy, scrollIntoView, scrollTo } = Element.prototype;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

function forceInstantScroll(args) {
    return !allowAnimations && args[0] && typeof args[0] === "object"
        ? [{ ...args[0], behavior: "instant" }, ...args.slice(1)]
        : args;
}

const animationChangeBus = new MockEventTarget();
const animationChangeCleanups = [];

let allowAnimations = true;
let allowTransitions = false;

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
    allowAnimations = true;
    allowTransitions = false;

    while (animationChangeCleanups.length) {
        animationChangeCleanups.pop()();
    }
}

/**
 * Turns off all animations triggered programmatically (such as with `animate`),
 * as well as smooth scrolls.
 *
 * @param {boolean} [enable=false]
 */
export function disableAnimations(enable = false) {
    ensureTest("disableAnimations");
    allowAnimations = enable;
}

/**
 * Restores all suppressed "animation" and "transition" properties for the current
 * test, as they are turned off by default.
 *
 * @param {boolean} [enable=true]
 */
export function enableTransitions(enable = true) {
    ensureTest("enableTransitions");
    allowTransitions = enable;
    animationChangeBus.dispatchEvent(new CustomEvent("toggle-transitions"));
}

/** @type {Element["animate"]} */
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
    $assign(this.style, style);

    // Return mock animation
    return new MockAnimation();
}

/** @type {Element["scroll"]} */
export function mockedScroll(...args) {
    return scroll.call(this, ...forceInstantScroll(args));
}

/** @type {Element["scrollBy"]} */
export function mockedScrollBy(...args) {
    return scrollBy.call(this, ...forceInstantScroll(args));
}

/** @type {Element["scrollIntoView"]} */
export function mockedScrollIntoView(...args) {
    return scrollIntoView.call(this, ...forceInstantScroll(args));
}

/** @type {Element["scrollTo"]} */
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
 * @param {(allowTransitions: boolean) => any} onChange
 */
export function subscribeToTransitionChange(onChange) {
    onChange(allowTransitions);
    animationChangeCleanups.push(
        on(animationChangeBus, "toggle-transitions", () => onChange(allowTransitions))
    );
}
