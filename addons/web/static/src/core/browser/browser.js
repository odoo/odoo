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
let localStorage = window.localStorage;
try {
    // Safari crashes in Private Browsing
    localStorage.setItem("__localStorage__", "true");
    localStorage.removeItem("__localStorage__");
} catch (_e) {
    localStorage = makeRAMLocalStorage();
    sessionStorage = makeRAMLocalStorage();
}

export const browser = {
    addEventListener: window.addEventListener.bind(window),
    removeEventListener: window.removeEventListener.bind(window),
    setTimeout: window.setTimeout.bind(window),
    clearTimeout: window.clearTimeout.bind(window),
    setInterval: window.setInterval.bind(window),
    clearInterval: window.clearInterval.bind(window),
    requestAnimationFrame: window.requestAnimationFrame.bind(window),
    cancelAnimationFrame: window.cancelAnimationFrame.bind(window),
    console: window.console,
    history: window.history,
    navigator,
    Notification: window.Notification,
    open: window.open.bind(window),
    SharedWorker: window.SharedWorker,
    Worker: window.Worker,
    XMLHttpRequest: window.XMLHttpRequest,
    localStorage,
    sessionStorage,
    fetch: window.fetch.bind(window),
    innerHeight: window.innerHeight,
    innerWidth: window.innerWidth,
    ontouchstart: window.ontouchstart,
};

Object.defineProperty(browser, "location", {
    set(val) {
        window.location = val;
    },
    get() {
        return window.location;
    },
    configurable: true,
});

Object.defineProperty(browser, "innerHeight", {
    get: () => window.innerHeight,
    configurable: true,
});
Object.defineProperty(browser, "innerWidth", {
    get: () => window.innerWidth,
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
            window.dispatchEvent(new StorageEvent("storage", { key, newValue: value }));
        },
        getItem(key) {
            return store[key];
        },
        clear() {
            store = {};
        },
        removeItem(key) {
            delete store[key];
            window.dispatchEvent(new StorageEvent("storage", { key, newValue: null }));
        },
        get length() {
            return Object.keys(store).length;
        },
        key() {
            return "";
        },
    };
}
