/** @odoo-module **/

import { browser } from "./browser";

// -----------------------------------------------------------------------------
// Feature detection
// -----------------------------------------------------------------------------

/**
 * true if the browser is based on Chromium (Google Chrome, Opera, Edge)
 *
 * @returns {boolean}
 */
export function isBrowserChrome() {
    return browser.navigator.userAgent.includes("Chrome");
}

export function isAndroid() {
    return /Android/i.test(browser.navigator.userAgent);
}

export function isIOS() {
    return /(iPad|iPhone|iPod)/i.test(browser.navigator.userAgent) ||
        (browser.navigator.platform === 'MacIntel' && maxTouchPoints() > 1);
}

export function isOtherMobileOS() {
    return /(webOS|BlackBerry|Windows Phone)/i.test(browser.navigator.userAgent);
}

export function isMacOS() {
    return Boolean(browser.navigator.userAgent.match(/Mac/i));
}

export function isMobileOS() {
    return isAndroid() || isIOS() || isOtherMobileOS();
}

export function isIosApp() {
    return /OdooMobile \(iOS\)/i.test(browser.navigator.userAgent);
}

export function hasTouch() {
    return "ontouchstart" in window || "onmsgesturechange" in window;
}

export function maxTouchPoints() {
    return browser.navigator.maxTouchPoints || 1;
}
