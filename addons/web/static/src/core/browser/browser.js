/** @odoo-module **/

/**
 * Browser
 *
 * This file exports an object containing common browser API. It may not look
 * incredibly useful, but it is very convenient when one needs to test code using
 * these methods. With this indirection, it is possible to patch the browser
 * object for a test.
 */

let sessionStorage = window.sessionStorage;
let localStorage = owl.browser.localStorage;
try {
    // Safari crashes in Private Browsing
    localStorage.setItem("__localStorage__", "true");
    localStorage.removeItem("__localStorage__");
} catch (e) {
    localStorage = makeRAMLocalStorage();
    sessionStorage = makeRAMLocalStorage();
}

export const browser = Object.assign({}, owl.browser, {
    addEventListener: window.addEventListener.bind(window),
    removeEventListener: window.removeEventListener.bind(window),
    requestAnimationFrame: window.requestAnimationFrame.bind(window),
    cancelAnimationFrame: window.cancelAnimationFrame.bind(window),
    console: window.console,
    history: window.history,
    navigator: navigator,
    open: window.open.bind(window),
    XMLHttpRequest: window.XMLHttpRequest,
    localStorage,
    sessionStorage,
});

Object.defineProperty(browser, "location", {
    set(val) {
        window.location = val;
    },
    get() {
        return window.location;
    },
    configurable: true,
});

// -----------------------------------------------------------------------------
// memory localStorage
// -----------------------------------------------------------------------------

/**
 * @returns {typeof window["localStorage"]}
 */
export function makeRAMLocalStorage() {
    let store = {};
    return {
        setItem(key, value) {
            store[key] = value;
        },
        getItem(key) {
            return store[key];
        },
        clear() {
            store = {};
        },
        removeItem(key) {
            delete store[key];
        },
        get length() {
            return Object.keys(store).length;
        },
        key() {
            return "";
        },
    };
}
