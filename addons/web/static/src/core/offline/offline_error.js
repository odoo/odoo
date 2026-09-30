import { usePlugin } from "@odoo/owl";
import { UncaughtPromiseError } from "../errors/error_service";
import { ConnectionLostError } from "../network/rpc";
import { registry } from "../registry";
import { OfflinePlugin } from "./offline_plugin";

const errorHandlerRegistry = registry.category("error_handlers");

// -----------------------------------------------------------------------------
// Fail to fetch errors
// -----------------------------------------------------------------------------

const fetchErrorMessages = [
    "Failed to fetch", // Chromium
    "Load failed", // WebKit
    "NetworkError when attempting to fetch resource.", // Firefox
];

/** @type {import("registries").ErrorHandler} */
export function offlineFailToFetchErrorHandler({ originalError }) {
    if (originalError instanceof TypeError && fetchErrorMessages.includes(originalError.message)) {
        const offlinePlugin = usePlugin(OfflinePlugin);
        offlinePlugin.setOffline(true);
        return true;
    }
}
errorHandlerRegistry.add("offlineFailToFetchErrorHandler", offlineFailToFetchErrorHandler, {
    sequence: 96,
});

// -----------------------------------------------------------------------------
// Lost connection errors
// -----------------------------------------------------------------------------

/** @type {import("registries").ErrorHandler} */
export function lostConnectionHandler({ error, originalError }) {
    if (!(error instanceof UncaughtPromiseError)) {
        return false;
    }
    if (originalError instanceof ConnectionLostError) {
        error.event.preventDefault();
        const offlinePlugin = usePlugin(OfflinePlugin);
        offlinePlugin.setOffline(true);
        return true;
    }
}
errorHandlerRegistry.add("lostConnectionHandler", lostConnectionHandler, { sequence: 98 });
