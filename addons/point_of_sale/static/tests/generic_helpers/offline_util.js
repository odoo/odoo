import { run } from "@point_of_sale/../tests/generic_helpers/utils";
import { ConnectionLostError } from "@web/core/network/rpc";

const originalFetch = window.fetch;
const originalSend = XMLHttpRequest.prototype.send;
const originalConsoleError = console.error;

export function setOfflineMode() {
    return run(() => {
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
    }, "Offline mode is now enabled");
}

export function setOnlineMode() {
    return run(() => {
        window.fetch = originalFetch;
        XMLHttpRequest.prototype.send = originalSend;
        console.error = originalConsoleError;
    }, "Offline mode is now disabled");
}
