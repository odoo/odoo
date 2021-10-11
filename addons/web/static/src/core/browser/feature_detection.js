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

export function isBrowserFirefox() {
    return browser.navigator.userAgent.includes("Firefox");
}

export function isMacOS() {
    return Boolean(browser.navigator.userAgent.match(/Mac/i));
}

export function isMobileOS() {
    return Boolean(
        browser.navigator.userAgent.match(/Android/i) ||
            browser.navigator.userAgent.match(/webOS/i) ||
            browser.navigator.userAgent.match(/iPhone/i) ||
            browser.navigator.userAgent.match(/iPad/i) ||
            browser.navigator.userAgent.match(/iPod/i) ||
            browser.navigator.userAgent.match(/BlackBerry/i) ||
            browser.navigator.userAgent.match(/Windows Phone/i)
    );
}

export function isIosApp() {
    return navigator.userAgent.match(/OdooMobile \(iOS\)/i);
}

export function hasTouch() {
    return "ontouchstart" in window || "onmsgesturechange" in window;
}

export function hasLegacyFilesystem() {
    return window['requestFileSystem'] || window['webkitRequestFileSystem'];
}
