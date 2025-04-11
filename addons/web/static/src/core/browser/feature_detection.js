/** @odoo-module **/

import { browser } from "./browser";

// -----------------------------------------------------------------------------
// Feature detection
// -----------------------------------------------------------------------------

/**
 * True if the browser is based on Chromium (Google Chrome, Opera, Edge).
 */
export function isBrowserChrome() {
    return /Chrome/i.test(browser.navigator.userAgent);
}

export function isBrowserFirefox() {
    return /Firefox/i.test(browser.navigator.userAgent);
}

/**
 * True if the browser is Microsoft Edge.
 */
export function isBrowserMicrosoftEdge() {
    return /Edg/i.test(browser.navigator.userAgent);
}

/**
 * true if the browser is based on Safari (Safari, Epiphany)
 *
 * @returns {boolean}
 */
export function isBrowserSafari() {
    return !isBrowserChrome() && browser.navigator.userAgent.includes("Safari");
}

export function isAndroid() {
    return /Android/i.test(browser.navigator.userAgent);
}

export function isIOS() {
    return (
        /(iPad|iPhone|iPod)/i.test(browser.navigator.userAgent) ||
        (browser.navigator.platform === "MacIntel" && maxTouchPoints() > 1)
    );
}

export function isOtherMobileOS() {
    return /(webOS|BlackBerry|Windows Phone)/i.test(browser.navigator.userAgent);
}

export function isMacOS() {
    return /Mac/i.test(browser.navigator.userAgent);
}

export function isMobileOS() {
    return isAndroid() || isIOS() || isOtherMobileOS();
}

export function isIosApp() {
    return /OdooMobile \(iOS\)/i.test(browser.navigator.userAgent);
}

export function isAndroidApp() {
    return /OdooMobile.+Android/i.test(browser.navigator.userAgent);
}

export function isDisplayStandalone() {
    return browser.matchMedia("(display-mode: standalone)").matches;
}

export function hasTouch() {
    return browser.ontouchstart !== undefined || browser.matchMedia("(pointer:coarse)").matches;
}

export function maxTouchPoints() {
    return browser.navigator.maxTouchPoints || 1;
}
