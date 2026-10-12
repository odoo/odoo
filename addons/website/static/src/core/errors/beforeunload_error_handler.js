import { registry } from "@web/core/registry";

const errorHandlerRegistry = registry.category("error_handlers");

let isUnloadingPage = false;
window.addEventListener("beforeunload", () => {
    isUnloadingPage = true;
    // restore after 10 seconds
    setTimeout(() => (isUnloadingPage = false), 10000);
});

/**
 * Handles the errors trigger after the before unload event.
 * @type {import("registries").ErrorHandler}
 */
function beforeUnloadHandler({ error }) {
    if (isUnloadingPage) {
        error.event.preventDefault();
        return true;
    }
    return false;
}

errorHandlerRegistry.add("beforeUnloadHandler", beforeUnloadHandler, { sequence: 1 });
