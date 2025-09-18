// @ts-check

/** @module @web/core/browser/feature_detection - Browser and device capability checks (Chrome, mobile, touch, PWA) */

import { browser } from "./browser";

// -----------------------------------------------------------------------------
// Feature detection
// -----------------------------------------------------------------------------

/**
 * True if the browser is based on Chromium (Google Chrome, Opera, Edge).
 *
 * @returns {boolean}
 */
export function isBrowserChrome() {
    return /Chrome/i.test(browser.navigator.userAgent);
}

/**
 * True if the browser is Firefox.
 *
 * @returns {boolean}
 */
export function isBrowserFirefox() {
    return /Firefox/i.test(browser.navigator.userAgent);
}

/**
 * True if the browser is Microsoft Edge.
 *
 * @returns {boolean}
 */
export function isBrowserMicrosoftEdge() {
    return /Edg/i.test(browser.navigator.userAgent);
}

/**
 * True if the browser is based on Safari (Safari, Epiphany).
 *
 * @returns {boolean}
 */
export function isBrowserSafari() {
    return !isBrowserChrome() && browser.navigator.userAgent?.includes("Safari");
}

/**
 * @returns {boolean}
 */
export function isAndroid() {
    return /Android/i.test(browser.navigator.userAgent);
}

/**
 * @returns {boolean}
 */
export function isIOS() {
    let isIOSPlatform = false;
    if ("platform" in browser.navigator) {
        isIOSPlatform = browser.navigator.platform === "MacIntel";
    }
    return (
        /(iPad|iPhone|iPod)/i.test(browser.navigator.userAgent) ||
        (isIOSPlatform && maxTouchPoints() > 1)
    );
}

/**
 * @returns {boolean}
 */
export function isOtherMobileOS() {
    return /(webOS|BlackBerry|Windows Phone)/i.test(browser.navigator.userAgent);
}

/**
 * @returns {boolean}
 */
export function isMacOS() {
    return /Mac/i.test(browser.navigator.userAgent);
}

/**
 * @returns {boolean}
 */
export function isMobileOS() {
    return isAndroid() || isIOS() || isOtherMobileOS();
}

/**
 * @returns {boolean}
 */
export function isIosApp() {
    return /OdooMobile \(iOS\)/i.test(browser.navigator.userAgent);
}

/**
 * @returns {boolean}
 */
export function isAndroidApp() {
    return /OdooMobile.+Android/i.test(browser.navigator.userAgent);
}

/**
 * @returns {boolean}
 */
export function isDisplayStandalone() {
    return browser.matchMedia("(display-mode: standalone)").matches;
}

/**
 * @returns {boolean}
 */
export function hasTouch() {
    return (
        browser.ontouchstart !== undefined ||
        browser.matchMedia("(pointer:coarse)").matches
    );
}

/**
 * @returns {number}
 */
export function maxTouchPoints() {
    return browser.navigator.maxTouchPoints || 1;
}

/**
 * @returns {boolean}
 */
export function isVirtualKeyboardSupported() {
    return "virtualKeyboard" in browser.navigator;
}
