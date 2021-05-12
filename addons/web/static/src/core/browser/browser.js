/** @odoo-module **/

// -----------------------------------------------------------------------------
// browser object
// -----------------------------------------------------------------------------

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
    console: window.console,
    location: window.location,
    history: window.history,
    navigator: navigator,
    open: window.open.bind(window),
    XMLHttpRequest: window.XMLHttpRequest,
    localStorage,
    sessionStorage,
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
