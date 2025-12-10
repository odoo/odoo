import { reactive } from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";

export const busLogsService = {
    dependencies: ["bus_service", "worker_service"],
    /**
     * @param {import("@web/env").OdooEnv}
     * @param {Partial<import("services").Services>} services
     */
    start(env, { bus_service, worker_service }) {
        const state = reactive({
            enabled: JSON.parse(localStorage.getItem("bus_log_menu.enabled")),
            enableLogging() {
                state.enabled = true;
                bus_service.setLoggingEnabled(true);
                localStorage.setItem("bus_log_menu.enabled", true);
            },
            disableLogging() {
                state.enabled = false;
                bus_service.setLoggingEnabled(false);
                localStorage.setItem("bus_log_menu.enabled", false);
            },
        });
        browser.addEventListener("storage", ({ key, newValue }) => {
            if (key === "bus_log_menu.enabled") {
                state.enabled = JSON.parse(newValue);
            }
        });
        worker_service.connectionInitializedDeferred.then(() => {
            bus_service.setLoggingEnabled(state.enabled);
        });
        odoo.busLogging = {
            stop: () => state.disableLogging(),
            start: () => state.enableLogging(),
            download: () => bus_service.downloadLogs(),
        };
        if (state.enabled) {
            console.log(
                "Bus logging is enabled. To disable it, use `odoo.busLogging.stop()`. To download the logs, use `odoo.busLogging.download()`."
            );
        }
        return state;
    },
};

registry.category("services").add("bus.logs_service", busLogsService);
