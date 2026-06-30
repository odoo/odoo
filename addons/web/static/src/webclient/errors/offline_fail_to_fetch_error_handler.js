import { ConnectionLostError } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";

const errorHandlerRegistry = registry.category("error_handlers");

const fetchErrorMessages = [
    "Failed to fetch", // Chromium
    "Load failed", // WebKit
    "NetworkError when attempting to fetch resource.", // Firefox
];

/**
 * @param {OdooEnv} env
 * @param {UncaughError} error
 * @param {Error} originalError
 * @returns {boolean}
 */
export function offlineFailToFetchErrorHandler(env, error, originalError) {
    if (originalError instanceof TypeError && fetchErrorMessages.includes(originalError.message)) {
        Promise.resolve().then(() => {
            throw new ConnectionLostError();
        });
        return true;
    }
}
errorHandlerRegistry.add("offlineFailToFetchErrorHandler", offlineFailToFetchErrorHandler, {
    sequence: 96,
});
