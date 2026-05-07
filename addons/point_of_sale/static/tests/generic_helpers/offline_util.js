import { run } from "@point_of_sale/../tests/generic_helpers/utils";
import { ConnectionLostError } from "@web/core/network/rpc";

const originalFetch = window.fetch;
const originalSend = XMLHttpRequest.prototype.send;
const originalConsoleError = console.error;
const OFFLINE_MODE_KEY = "pos.tests.offline_mode";

const navigatorPrototype = Object.getPrototypeOf(window.navigator);
const originalNavigatorOnLine =
    navigatorPrototype && Object.getOwnPropertyDescriptor(navigatorPrototype, "onLine");

/**
 * Utility functions to simulate offline/online mode in tests. The offline mode is persisted through page reloads
 * in the same browser tab, allowing to test the behavior of the application when reloading while being offline.
 */
function persistOfflineState(enabled) {
    if (enabled) {
        sessionStorage.setItem(OFFLINE_MODE_KEY, "1");
    } else {
        sessionStorage.removeItem(OFFLINE_MODE_KEY);
    }
}

function applyOfflineOverrides() {
    Object.defineProperty(navigatorPrototype, "onLine", {
        configurable: true,
        get: () => false,
    });
    window.dispatchEvent(new Event("offline"));

    window.fetch = () => {
        throw new ConnectionLostError();
    };
    XMLHttpRequest.prototype.send = () => {
        throw new ConnectionLostError();
    };

    console.error = (...args) => {
        const message = args[0] instanceof Error ? args[0].message : args[0];
        if (typeof message === "string" && message.includes("ConnectionLostError")) {
            console.info("Connection lost error handled in offline mode:", ...args);
        } else {
            originalConsoleError.apply(console, args);
        }
    };
}

function restoreOnlineOverrides() {
    Object.defineProperty(navigatorPrototype, "onLine", originalNavigatorOnLine);
    window.fetch = originalFetch;
    XMLHttpRequest.prototype.send = originalSend;
    console.error = originalConsoleError;
    window.dispatchEvent(new Event("online"));
}

if (sessionStorage.getItem(OFFLINE_MODE_KEY) === "1") {
    applyOfflineOverrides();
}

export function setOfflineMode() {
    return run(() => {
        persistOfflineState(true);
        applyOfflineOverrides();
    }, "Offline mode is now enabled");
}

export function setOnlineMode() {
    return run(() => {
        persistOfflineState(false);
        restoreOnlineOverrides();
    }, "Offline mode is now disabled");
}
